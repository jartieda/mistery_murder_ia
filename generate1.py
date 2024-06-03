# %%
#configure enviroment variables for gpt

import os
import random
#from langchain.llms import AzureOpenAI
from langchain_openai import OpenAI
from langchain_openai import AzureOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field


from dotenv import load_dotenv
load_dotenv("env_openai")

# %%

#configure enviroment variables for gpt

#os.environ["OPENAI_API_TYPE"] = openai_instance["api_type"]
print(os.environ["OPENAI_API_KEY"])

#os.environ["OPENAI_API_BASE"] = openai_instance["api_base"]
#os.environ["OPENAI_API_VERSION"] = openai_instance["api_version"]


# %%
from langchain_core.prompts import PromptTemplate

from langchain_core.output_parsers import StrOutputParser

#llm = OpenAI()


from langchain_nvidia_ai_endpoints import ChatNVIDIA

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
                    input_variables=["name", "short_description"]) |llm

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
                            input_variables=["victim_name", "victim_short_description", "name", "shrt_bio"])|llm

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
    input_variables=["character", "victim", "secret_holder"])|llm

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
    input_variables=[ "victim", "murderer"])|llm

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
    witness: str = Field(description="name of the character who can confirm the alibi")
    alibi: str = Field(description="alibi")

 # Set up a parser + inject instructions into the prompt template.
parserAlibi = JsonOutputParser(pydantic_object=Alibi)   

templae_alibi="""generate an alibi for this character {character}. 
Any of the characters of the story must be able to confirm the alibi in any way. 
The alibi is something the witness know that makes imposible that {character} has murdered the victim.
The witness cannot be {character}
The murder circustances were: {circustances}
The characters of the story are: {rest_chars}

"""
templae_alibi += "Give the answer in the following format: \n {format_instructions}\n"
rest_chars = ""
for c in chars_final:
    rest_chars += f" * {c['name']} - {c['short']} - {c['motive']} - {c['secret']} \n"

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
            if cc['name'] == alib['witness']:
                print("found witness", cc['name'])
                if not 'others_alibi' in cc:
                    cc['others_alibi'] = [alib['alibi'],]
                else:
                    cc['others_alibi'].append(alib['alibi'])
                break
        print(c['name'], c['alibi'])

# %%

result = {"characters": chars_final, 
          "victim": victim,
          "murderer": murderer,
          "solution": murder_circustances}

print(result)
import json
with open('temp.json', 'w') as file:
    json.dump(result, file)

    
# %%

# number_of_hours = 5
# template_murder_dates = """generate a timetable for a mistery murder game for the {number_of_hours} hours previous to the murder of {victim}. 
# the crime circuastances are : {details} time of death is estimated at {time_of_death} 
# with the location and activities of the following characters: \n"""
# for c in chars_final:
#     template_murder_dates += f" * {c['name']} - {c['short']} -  {c['motive']} \n"
# template_murder_dates += f"{victim['name']} - {victim['short']}\n"
# template_murder_dates += "the murdere is : {murderer} \n"
# template_murder_dates += """provide a location and activity for each character for the {number_of_hours} hours previous to the time of death\n"""
# template_murder_dates += """ use the following format: <name of the character> - <time> - <activity> - <location>\n"""
# print(template_murder_dates)

# llm_dates = LLMChain(prompt=PromptTemplate(template=template_murder_dates, 
#                         input_variables=["number_of_hours", "victim","murderer", "details", "time_of_death"]),
#                           llm=llm)
# timetable = llm_dates.run({'number_of_hours': str(number_of_hours),
#                             'victim':victim['name'], 
#                             'murderer':chars_final[murderer]['name'],
#                             'details':murder_circustances, 
#                             'time_of_death':murder_hour})

# print(timetable)

# %%
