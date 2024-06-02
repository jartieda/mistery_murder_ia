# %%
#configure enviroment variables for gpt

import os
import random
from langchain.llms import AzureOpenAI
# %%

#configure enviroment variables for gpt

#os.environ["OPENAI_API_TYPE"] = openai_instance["api_type"]
os.environ["OPENAI_API_KEY"] = 'kk'

#os.environ["OPENAI_API_BASE"] = openai_instance["api_base"]
#os.environ["OPENAI_API_VERSION"] = openai_instance["api_version"]



def get_chat_model(streaming=False, temperature=0.0, handler=None):
    '''
    return  VertexAI( streaming=True,
        callbacks=BaseCallbackManager([handler]),
    )

    '''
    
    return AzureOpenAI(
            deployment_name="gpt-35-turbo",
            model_name="gpt-35-turbo",  
            temperature=temperature
        )

    '''
    return AzureChatOpenAI(
        openai_api_base=os.environ["OPENAI_API_BASE"],
        openai_api_version=os.environ["OPENAI_API_VERSION"],
        deployment_name=DEPLOYMENT_NAME,
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_api_type=os.environ["OPENAI_API_TYPE"],
        temperature=temperature,
        streaming=streaming,
        callback_manager=BaseCallbackManager([handler]),
        verbose=True,
    )
    '''

# %%
from langchain.llms import OpenAI
from langchain import PromptTemplate, LLMChain


llm = OpenAI()


# %%
#generte characters
number_of_characters = 4
template_gen_chars = """Generate {number_of_characters} characters of a mistery murder game. 
do not generate a character for the victim. 
Give the answer in the following form: 'Character: <name of the character> - <short description of the character>'

"""
llm_chain_gen_chars = LLMChain(prompt=PromptTemplate(template=template_gen_chars, 
                                           input_variables=["number_of_characters"]), llm=llm)
chars_raw = llm_chain_gen_chars.run(number_of_characters)
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
chars_expand_llm = LLMChain(prompt=PromptTemplate(template=template_expand_char, 
    input_variables=["name", "short_description"]), llm=llm)

for c in chars_final:
    c['long_bio'] = chars_expand_llm.run({'name':c['name'], 'short_description':c['short']})
    print(c)

# %%
template_victim = "Generate a character for a posible vicitim in a mystery murder gaim with the following characters:\n"
for c in chars_final:
    template_victim += f" * {c['name']} - {c['short']}\n"

template_victim += "Give the answer in the following form: '<name of the character> - <short description of the character> - <long bio of the character>'\n"
print(template_victim)

victim_llm = LLMChain(prompt=PromptTemplate(template=template_victim, input_variables=[]) , llm=llm)
victimraw = victim_llm.run({})
print(victimraw)
victimaray = victimraw.split(" - ")
victim = {'name':victimaray[0], 'short':victimaray[1], 'long_bio':victimaray[2]}
print(victim)

# %%
tempale_motive = "Generate a motive for a killing vicitim {victim_name} - {victim_short_description} in a mystery murder game for the following character {name} - {shrt_bio}:\n"
llm_motiv = LLMChain(prompt=PromptTemplate(template=tempale_motive, 
                                           input_variables=["victim_name", "victim_short_description", "name", "shrt_bio"]), llm=llm)

for c in chars_final:
    motive = llm_motiv.run({'victim_name':victim['name'], 'victim_short_description':victim['short'], 
                            'name':c['name'], 'shrt_bio':c['short']})
    print(motive)
    c['motive'] = motive

# %%
tempale_secret = """generate a secret that {secret_holder} knows about the relation of {character} with {victim}. 
the secret is related whith the murder of {victim} in a mistery murder game but gives no information about the murder itself.
the game has the following characters: \n"""
for c in chars_final:
    tempale_secret += f" * {c['name']} - {c['short']} -  {c['motive']} \n"
tempale_secret += f"{victim['name']} - {victim['short']}\n"
llm_secret = LLMChain(prompt=PromptTemplate(template=tempale_secret, 
    input_variables=["character", "victim", "secret_holder"]), llm=llm)

for i in range(len(chars_final)):
    if i == len(chars_final) - 1:
        dest = 0
    else:
        dest = i+1

    chars_final[i]['secret']= llm_secret.run({'character':chars_final[i]['name'],
                                               'victim':victim['name'], 
                                               'secret_holder':chars_final[dest]['name']})
    print(chars_final[i]['secret'])
# %%
tempale_murder = """for a mistery murder game describe circustances and the crime scene of the murder of {victim} by {murderer} and the time of death. \n"""
tempale_murder += f"the victim is {victim['name']} - {victim['short']}\n"
tempale_murder += "the characters of the game are: \n"""
for c in chars_final:
    tempale_murder += f" * {c['name']} - {c['short']} - {c['motive']} - {c['secret']} \n"
tempale_murder += "use the following formt <time of death> - <circustances> "

llm_murder = LLMChain(prompt=PromptTemplate(template=tempale_murder, 
    input_variables=[ "victim", "murderer"]), llm=llm)

murderer = random.randint(0, len(chars_final)-1)

murder_circustances_raw = llm_murder.run({'victim':victim['name'], 
                                      'murderer':chars_final[murderer]['name']
                                    })
murder_split = murder_circustances_raw.split(" - ")
if (len(murder_split) == 2):
    murder_circustances = murder_split[1]
    murder_hour = murder_split[0]


print(murder_hour, murder_circustances)


# %%
number_of_hours = 5
template_murder_dates = """generate a timetable for a mistery murder game for the {number_of_hours} hours previous to the murder of {victim}. 
the crime circuastances are : {details} time of death is estimated at {time_of_death} 
with the location and activities of the following characters: \n"""
for c in chars_final:
    template_murder_dates += f" * {c['name']} - {c['short']} -  {c['motive']} \n"
template_murder_dates += f"{victim['name']} - {victim['short']}\n"
template_murder_dates += "the murdere is : {murderer} \n"
template_murder_dates += """provide a location and activity for each character for the {number_of_hours} hours previous to the time of death\n"""
template_murder_dates += """ use the following format: <name of the character> - <time> - <activity> - <location>\n"""
print(template_murder_dates)

llm_dates = LLMChain(prompt=PromptTemplate(template=template_murder_dates, 
                        input_variables=["number_of_hours", "victim","murderer", "details", "time_of_death"]),
                          llm=llm)
timetable = llm_dates.run({'number_of_hours': str(number_of_hours),
                            'victim':victim['name'], 
                            'murderer':chars_final[murderer]['name'],
                            'details':murder_circustances, 
                            'time_of_death':murder_hour})

print(timetable)

# %%
