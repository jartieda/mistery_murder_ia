from langchain.pydantic_v1 import BaseModel, Field
from typing import List, Dict, Any, Optional
from langchain_core.prompts import PromptTemplate

from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_nvidia_ai_endpoints import ChatNVIDIA

llm = ChatNVIDIA(model="mistralai/mixtral-8x7b-instruct-v0.1")


# Character Generation

class Character(BaseModel):
    name: str = Field(description="name of the character")
    short: str = Field(description="short description of the character")
    longbio: str = Field(description="long bio of the character")

class CharsList(BaseModel):
    characters: List[Character] = Field(description="list of characters")

# Set up a parser + inject instructions into the prompt template.
parserChars = JsonOutputParser(pydantic_object=CharsList)   

class llm_chain_gen_chars_Input(BaseModel):
    number_of_characters: int = Field(description="number of characters")
class llm_chain_gen_chars_Input2(BaseModel):
    input: llm_chain_gen_chars_Input = Field(description="field named input")

template_gen_chars = """Generate {number_of_characters} characters of a mistery murder game. 
do not generate a character for the victim. None of them should be a detective or a policeman. None of them is the murderer
Give the answer in the following form:  
{format_instructions}

"""
print(parserChars.get_format_instructions())

llm_chain_gen_chars = PromptTemplate(template=template_gen_chars, 
                                     input_variables=["number_of_characters"],
                                     partial_variables={"format_instructions":parserChars.get_format_instructions()})|llm|parserChars


# Character generation expansion

class chars_expand_llm_Input(BaseModel):
    name: str = Field(description="character name")
    short_description: str = Field(description="short character description")
class chars_expand_llm_Input2(BaseModel):
    input: chars_expand_llm_Input = Field(description="field named input")

template_expand_char = """expanad the bio for the character named {name} for a mistery murder game 
according to a short description of {short_description}. """

llm_chars_expand = PromptTemplate(template=template_expand_char, 
                    input_variables=["name", "short_description"]) |llm|StrOutputParser()


# Victim Generation

# Set up a parser + inject instructions into the prompt template.
parser_victim = JsonOutputParser(pydantic_object=Character)   

template_victim = """Generate a character for a posible vicitim in a mystery murder game
 with the following characters:\n{characters}\n"""
#for c in chars_final:
#    template_victim += f" * {c['name']} - {c['short']}\n"

template_victim += "Give the answer in the following format: \n {format_instructions}\n"
print(template_victim)

victim_llm = PromptTemplate(template=template_victim,
                            input_variables=['characters'],
                            partial_variables={"format_instructions":parser_victim.get_format_instructions()}) |llm|parser_victim


# motive generation
tempale_motive = "Generate a motive for a killing vicitim {victim_name} - {victim_short_description} in a mystery murder game for the following character {name} - {shrt_bio}:\n"
llm_motiv = PromptTemplate(template=tempale_motive, 
                            input_variables=["victim_name", "victim_short_description", "name", "shrt_bio"])|llm|StrOutputParser()

tempale_secret = """generate a secret that {secret_holder} knows about the relation of {character} with {victim}. 
the secret is related whith the murder of {victim} in a mistery murder game but gives no information about the murder itself.\n
the secret is something that {character} doesn't want to be known but {secret_holder} knows.
the secret doesn't reveal who murdered {victim}.
The game has the following characters: 
{character_full} 
The victim is: 
{victim} - {victim_short}"""
#for c in chars_final:
#    tempale_secret += f" * {c['name']} - {c['short']} -  {c['motive']} \n"
#tempale_secret += f"the victim: \n {victim['name']} - {victim['short']}\n"

print(tempale_secret)

llm_secret = PromptTemplate(template=tempale_secret, 
    input_variables=["character", "victim",
                      "secret_holder", "character_full",
                      "victim_short"])|llm|StrOutputParser()

# murder circustances

class llm_murder_Input(BaseModel):
    victim: str = Field(description="victim name")
    victim_short: str = Field(description="short description of the victim")
    murderer: str = Field(description="murderer name")
    characters: List[Character] = Field(description="list of characters")

class llm_murder_Input2(BaseModel):
    input: llm_murder_Input = Field(description="field named input")

tempale_murder = """for a mistery murder game describe circustances and the crime scene of the murder of {victim} by the hands of {murderer} and the time of death. \n"""
tempale_murder += "the victim is {victim} - {victim_short}\n"
tempale_murder += "the characters of the game are: {characters}\n"""

#for c in chars_final:
#    tempale_murder += f" * {c['name']} - {c['short']} - {c['motive']} - {c['secret']} \n"
tempale_murder += "use the following format <time of death> - <circustances> "

llm_murder = PromptTemplate(template=tempale_murder, 
    input_variables=[ "victim", "murderer", "characters"])|llm|StrOutputParser()

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
- The witness cannot be itself
- The witness cannot be the victim
- Use the exact names to refer to the characers 

The murder circustances were: {circustances}
The characters of the story are: {rest_chars}
"""
templae_alibi += "Give the answer in the following format: \n {format_instructions}\n"

llm_alibi = PromptTemplate(template=templae_alibi, 
                                input_variables=["character", "rest_chars", "circustances"],
                                partial_variables={"format_instructions":parserAlibi.get_format_instructions()}) |llm|parserAlibi
