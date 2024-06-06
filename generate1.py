# %%
import random
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.docstore.document import Document
import networkx as nx
import matplotlib.pyplot as plt
import json

from langchain_community.graphs.graph_document import (
    Node as BaseNode,
    Relationship as BaseRelationship
)
from typing import List, Dict, Any, Optional
from langchain.pydantic_v1 import Field, BaseModel


from dotenv import load_dotenv
load_dotenv("env_keys")

# %%


llm = ChatNVIDIA(model="mistralai/mixtral-8x7b-instruct-v0.1")


# %% 
#generte characters
number_of_characters = 4
template_gen_chars = """Generate {number_of_characters} characters of a mistery murder game. 
do not generate a character for the victim. None of them should be a detective or a policeman. None of them is the murderer
Give the answer in the following form: 'Character: <name of the character> - <short description of the character>'

"""

#llm_chain_gen_chars = LLMChain(prompt=PromptTemplate(template=template_gen_chars, 
#                                           input_variables=["number_of_characters"]), llm=llm)

llm_chain_gen_chars = PromptTemplate(template=template_gen_chars, input_variables=["number_of_characters"])|llm|StrOutputParser()

chars_raw = llm_chain_gen_chars.invoke({"number_of_characters": number_of_characters})

print(chars_raw)
chars_array = chars_raw.split("Character: ")
chars_final = []
for c in chars_array:
    print(c)
    p = c.split(" - ")
    if len(p) == 2:
        chars_final.append({'name':p[0], 'short':p[1]})
print(chars_final)


# %%
template_expand_char = """expanad the bio for the character named {name} for a mistery murder game 
according to a short description of {short_description}. """


chars_expand_llm = PromptTemplate(template=template_expand_char, 
                    input_variables=["name", "short_description"]) |llm|StrOutputParser()

for c in chars_final:
    c['longbio'] = chars_expand_llm.invoke({'name':c['name'], 'short_description':c['short']})
    print(c)


# %%

# Define your desired data structure.
class Character(BaseModel):
    name: str = Field(description="name of the character")
    short: str = Field(description="short description of the character")
    longbio: str = Field(description="long bio of the character")

 # Set up a parser + inject instructions into the prompt template.
parser = JsonOutputParser(pydantic_object=Character)   

template_victim = "Generate a character for a posible vicitim in a mystery murder game with the following characters:\n"
for c in chars_final:
    template_victim += f" * {c['name']} - {c['short']}\n"

template_victim += "Give the answer in the following format: \n {format_instructions}\n"
print(template_victim)

victim_llm = PromptTemplate(template=template_victim,
                            input_variables=[],
                             partial_variables={"format_instructions":parser.get_format_instructions()}) |llm|parser
victimraw = victim_llm.invoke({})
print(victimraw)
victim = victimraw
print(victim)

# %%
tempale_motive = "Generate a motive for a killing vicitim {victim_name} - {victim_short_description} in a mystery murder game for the following character {name} - {shrt_bio}:\n"
llm_motiv = PromptTemplate(template=tempale_motive, 
                            input_variables=["victim_name", "victim_short_description", "name", "shrt_bio"])|llm|StrOutputParser()

for c in chars_final:
    motive = llm_motiv.invoke({'victim_name':victim['name'], 'victim_short_description':victim['short'], 
                            'name':c['name'], 'shrt_bio':c['short']})
    print(motive)
    c['motive'] = motive

# %%
tempale_secret = """generate a secret that {secret_holder} knows about the relation of {character} with {victim}. 
the secret is related whith the murder of {victim} in a mistery murder game but gives no information about the murder itself.\n
the secret is something that {character} doesn't want to be known but {secret_holder} knows.
the secret doesn't reveal who murdered {victim}.
The game has the following characters: \n"""
for c in chars_final:
    tempale_secret += f" * {c['name']} - {c['short']} -  {c['motive']} \n"
tempale_secret += f"the victim: \n {victim['name']} - {victim['short']}\n"

print(tempale_secret)

llm_secret = PromptTemplate(template=tempale_secret, 
    input_variables=["character", "victim", "secret_holder"])|llm|StrOutputParser()

for i in range(len(chars_final)):
    if i == len(chars_final) - 1:
        dest = 0
    else:
        dest = i+1

    chars_final[dest]['secret']= llm_secret.invoke({'character':chars_final[i]['name'],
                                               'victim':victim['name'], 
                                               'secret_holder':chars_final[dest]['name']})
    print("--------\n", chars_final[i]['name'], 
          "known by:" , chars_final[dest]['name'],
          "---", chars_final[dest]['secret'])

# %%
# random selection of murderer 
murderer = random.randint(0, len(chars_final)-1)
print(f"the murderer is {chars_final[murderer]['name']}")

# %%
tempale_murder = """for a mistery murder game describe circustances and the crime scene of the murder of {victim} by the hands of {murderer} and the time of death. \n"""
tempale_murder += f"the victim is {victim['name']} - {victim['short']}\n"
tempale_murder += "the characters of the game are: \n"""
for c in chars_final:
    tempale_murder += f" * {c['name']} - {c['short']} - {c['motive']} - {c['secret']} \n"
tempale_murder += "use the following format <time of death> - <circustances> "

llm_murder = PromptTemplate(template=tempale_murder, 
    input_variables=[ "victim", "murderer"])|llm|StrOutputParser()

murder_circustances_raw = llm_murder.invoke({'victim':victim['name'], 
                                      'murderer':chars_final[murderer]['name']
                                    })
murder_split = murder_circustances_raw.split(" - ")
if (len(murder_split) == 2):
    murder_circustances = murder_split[1]
    murder_hour = murder_split[0]

    print(murder_hour, murder_circustances)
else: 
    murder_circustances = murder_circustances_raw
    print(murder_circustances)

# %%
# generate an alibi for everybody except for teh murderer
# Define your desired data structure.
class Alibi(BaseModel):
    witness: str = Field(description="name of the character who can confirm the alibi. use the exact name provided.")
    alibi: str = Field(description="alibi")

 # Set up a parser + inject instructions into the prompt template.
parserAlibi = JsonOutputParser(pydantic_object=Alibi)   

templae_alibi="""generate an alibi for this character {character}. 

- Any of the characters of the story must be able to confirm the alibi in any way. 
- The alibi is something the witness know that makes imposible that {character} has murdered the victim.
- The witness cannot be {character}
- The witness cannot be the victim
- Use the exact names to refer to the characers 

The murder circustances were: {circustances}
The characters of the story are: {rest_chars}
"""
templae_alibi += "Give the answer in the following format: \n {format_instructions}\n"
rest_chars = ""
for c in chars_final:
    rest_chars += f" - **{c['name']}** - {c['short']} - {c['motive']} - {c['secret']} \n"

for c in chars_final:
    if c != chars_final[murderer]:
        llm_alibi = PromptTemplate(template=templae_alibi, 
                                input_variables=["character", "rest_chars", "circustances"],
                                partial_variables={"format_instructions":parserAlibi.get_format_instructions()}) |llm|parserAlibi
        alib = llm_alibi.invoke({"character": c["name"], 
                                 "rest_chars": rest_chars, 
                                 "circustances": murder_circustances})  
        
        c['alibi'] = alib['alibi']
        for cc in chars_final: 

            if cc['name'].replace('"',"'") == alib['witness'].replace('"',"'"):
                print("found witness", cc['name'])
                if not 'others_alibi' in cc:
                    cc['others_alibi'] = [alib['alibi'],]
                else:
                    cc['others_alibi'].append(alib['alibi'])
                break
        print(c['name'], "witness: ", alib['witness'], " - ", c['alibi'])

# %%

result = {"characters": chars_final, 
          "victim": victim,
          "murderer": murderer,
          "solution": murder_circustances}

print(result)
with open('temp.json', 'w') as file:
    json.dump(result, file)



# %%
## write the full story

result_md = "# Mistery Murder Game\n"

result_md += "## Characters\n"

for c in result["characters"]:
    result_md += f"### **{c['name']}** \n {c['short']}\n"
    if "others_alibi" in c:
        result_md += "#### alibis for other characters\n"
        for a in c['others_alibi']:
            result_md += f" - {a}\n"
    result_md += f"#### secrets known about other characters \n{c['secret']}\n"

result_md += "## Victim\n"
result_md +=  f"- **{victim['name']}** {victim['short']}\n"

result_md += "## Murderer\n"
result_md += f"The murderer is {result['characters'][murderer]['name']}\n"
result_md += "### Circustances of the murder\n"
result_md += murder_circustances + "\n"

# save result_md to a file with .md extension
with open('temp.md', 'w') as file:
    file.write(result_md)

print(result_md)

# %%





# %%


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
    
# %%
doc =  Document(page_content=result_md, metadata={"source": "local"})

graphout = extract_and_store_graph(doc,nodes = ["peron", "victim"], rels=["knows_about", "murdered", "alibi",
                                          "motive"])

# %%


# Create a knowledge graph
G = nx.DiGraph()
for r in graphout['nodes']:
    G.add_node(r['id'], label=r['type'])
for r in graphout['rels']:
    if 'type' in r:
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
# %%

# %%
