# %%
import random
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import PromptTemplate
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
from langgraph.prebuilt import create_react_agent
from langchain_core.messages.human import HumanMessage
from langchain.tools import StructuredTool, BaseTool

from dotenv import load_dotenv
load_dotenv("env_keys")

from aux_tools import render_text_description_and_nested_args
from mm_tools import (llm_chain_gen_chars, llm_chars_expand, victim_llm,
                        llm_secret, llm_murder, llm_alibi, llm_motiv)
from mm_graph import draw_graph, extract_and_store_graph
# %%
llm = ChatNVIDIA(model="mistralai/mixtral-8x7b-instruct-v0.1")

# %% 
#generte characters
number_of_characters = 6

chars_raw = llm_chain_gen_chars.invoke({"number_of_characters": number_of_characters})

print(chars_raw)
# %%
#chars_array = chars_raw.split("Character: ")
#chars_final = []
#for c in chars_array:
#    print(c)
#    p = c.split(" - ")
#    if len(p) == 2:
#        chars_final.append({'name':p[0], 'short':p[1]})
#print(chars_final)
chars_final = chars_raw['characters']
print(chars_final)
# %%
#for c in chars_final:
#    c['longbio'] = llm_chars_expand.invoke({'name':c['name'], 'short_description':c['short']})
#    print(c)
 
# %%

victimraw = victim_llm.invoke({'characters': chars_final})
victim = victimraw
print(victim)

# %%
for c in chars_final:
    print(c)
    motive = llm_motiv.invoke({'victim_name':victim['name'], 
                               'victim_short_description':victim['short'], 
                               'name':c['name'], 'shrt_bio':c['short']})
    print(motive)
    c['motive'] = motive

# %%

for i in range(len(chars_final)):
    if i == len(chars_final) - 1:
        dest = 0
    else:
        dest = i+1

    chars_final[dest]['secret']= llm_secret.invoke({'character':chars_final[i]['name'],
                                               'victim':victim['name'], 
                                               'victim_short': victim['short'],
                                               'secret_holder':chars_final[dest]['name'],
                                               'character_full': chars_final})
    print("--------\n", chars_final[i]['name'], 
          "known by:" , chars_final[dest]['name'],
          "---", chars_final[dest]['secret'])

# %%
# random selection of murderer 
murderer = random.randint(0, len(chars_final)-1)
print(f"the murderer is {chars_final[murderer]['name']}")

# %%

murder_circustances_raw = llm_murder.invoke({'victim':victim['name'], 
                                             'victim_short': victim['short'],
                                      'murderer':chars_final[murderer]['name'], 
                                      'characters': chars_final
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

rest_chars = ""
for c in chars_final:
    rest_chars += f" - **{c['name']}** - {c['short']} - {c['motive']} - {c['secret']} \n"

for c in chars_final:
    if c != chars_final[murderer]:
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
doc =  Document(page_content=result_md, metadata={"source": "local"})

graphout = extract_and_store_graph(doc,nodes = ["peron", "victim"], rels=["knows_about", "murdered", "alibi",
                                          "motive"])

draw_graph(graphout)
# %%



# %%

# %%

# %%
