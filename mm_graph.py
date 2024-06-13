# %%
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List, Dict, Any, Optional
from langchain_community.graphs.graph_document import (
    Node as BaseNode,
    Relationship as BaseRelationship
)
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
import json
from langchain.docstore.document import Document

import networkx as nx
import matplotlib.pyplot as plt


class Property(BaseModel):
  """A single property consisting of key and value"""
  key: str = Field(..., description="key")
  value: str = Field(..., description="value")

class Node(BaseNode):
    properties: Optional[List[Property]] = Field(
        None, description="List of node properties")

class Relationship(BaseRelationship):
    properties: Optional[List[Property]] = Field(
        None, description="List of relationship properties"
    )
class KnowledgeGraph(BaseModel):
    """Generate a knowledge graph with entities and relationships."""
    nodes: List[BaseNode] = Field(
        ..., description="List of nodes in the knowledge graph")
    rels: List[BaseRelationship] = Field(
        ..., description="List of relationships in the knowledge graph"
    )


# %%
llm_long_output = ChatNVIDIA(model="mistralai/mixtral-8x7b-instruct-v0.1", 
                             max_tokens=3000,
                             temperature=1,)

def get_extraction_chain(
    allowed_nodes: Optional[List[str]] = None,
    allowed_rels: Optional[List[str]] = None
    ):
    prompt = f"""# Knowledge Graph Instructions 
    [INST] 
## 1. Overview
You are a top-tier algorithm designed for extracting information in structured formats to build a knowledge graph.
- **Nodes** represent entities and concepts. They're akin to Wikipedia nodes.
- The aim is to achieve simplicity and clarity in the knowledge graph, making it accessible for a vast audience.
## 2. Labeling Nodes
- **Consistency**: Ensure you use basic or elementary types for node labels.
  - For example, when you identify an entity representing a person, always label it as **"person"**. Avoid using more specific terms like "mathematician" or "scientist".
- **Node IDs**: Never utilize integers as node IDs. Node IDs should be names or human-readable identifiers found in the text.
{'- **Allowed Node Labels:**' + ", ".join(allowed_nodes) if allowed_nodes else ""}
{'- **Allowed Relationship Types**:' + ", ".join(allowed_rels) if allowed_rels else ""}
## 3. Handling Numerical Data and Dates
- Numerical data, like age or other related information, should be incorporated as attributes or properties of the respective nodes.
- **No Separate Nodes for Dates/Numbers**: Do not create separate nodes for dates or numerical values. Always attach them as attributes or properties of nodes.
- **Property Format**: Properties must be in a key-value format.
- **Quotation Marks**: Never use escaped single or double quotes within property values.
- **Naming Convention**: Use camelCase for property keys, e.g., `birthDate`.
## 4. Coreference Resolution
- **Maintain Entity Consistency**: When extracting entities, it's vital to ensure consistency.
If an entity, such as "John Doe", is mentioned multiple times in the text but is referred to by different names or pronouns (e.g., "Joe", "he"), 
always use the most complete identifier for that entity throughout the knowledge graph. In this example, use "John Doe" as the entity ID.  
Remember, the knowledge graph should be coherent and easily understandable, so maintaining consistency in entity references is crucial. 
## 5. Strict Compliance
Adhere to the rules strictly. Non-compliance will result in termination.
## 6. Format
Use the following format for the output: """ +"{format_instructions}"
    prompt += "[/INST] \n"
    prompt +=  "Use the given format to extract information from the following input: {input}\n"
    prompt += "Tip: Make sure to answer in the correct format\n"

    
    # Set up a parser + inject instructions into the prompt template.
    parser = JsonOutputParser(pydantic_object=KnowledgeGraph)   


    graph_llm = PromptTemplate(template=prompt,
                                input_variables=["input",],
                                partial_variables={"format_instructions":parser.get_format_instructions()}) |llm_long_output|parser
    return graph_llm


def extract_and_store_graph(
            document: Document,
            nodes:Optional[List[str]] = None,
            rels:Optional[List[str]]=None
        ) -> None:
    # Extract graph data using OpenAI functions
    extract_chain = get_extraction_chain(nodes, rels)
    data = extract_chain.invoke(document.page_content)

    #print the data formated
    print(json.dumps(data, indent=2))
    #print(data)
    return data


def draw_graph(graphout):
    # Create a knowledge graph
    G = nx.DiGraph()
    for r in graphout['nodes']:
        G.add_node(r['id'], label=r['type'])
    for r in graphout['rels']:
        if ('type' in r and 'source' in r and 'target' in r and
            r['type'] is not None and 
            r['source'] is not None and
            r['target'] is not None):
            G.add_edge(r['source'], r['target'], label=r['type'])
        
    # Visualize the knowledge graph
    pos = nx.spring_layout(G, seed=42, k=0.9)
    labels = nx.get_edge_attributes(G, 'label')
    plt.figure(figsize=(8, 8))
    # Color nodes based on their type
    colors = []
    for node in G.nodes(data=True):
        if node[1]['label'] == 'person':
            colors.append('lightblue')
        elif node[1]['label'] == 'victim':
            colors.append('red')
        else:
            colors.append('lightcoral')

    # Draw the graph
    nx.draw(G, pos, with_labels=True, font_size=12, node_size=700, node_color=colors, edge_color='gray', alpha=0.6)
    #nx.draw(G, pos, with_labels=True, font_size=12, node_size=700, node_color='lightblue', edge_color='gray', alpha=0.6)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=8, label_pos=0.3, verticalalignment='baseline')
    plt.title('Knowledge Graph')
    plt.show()