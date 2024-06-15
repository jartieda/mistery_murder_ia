# %%
from langchain_nvidia_ai_endpoints import ChatNVIDIA

from langchain.tools import StructuredTool

from langchain import hub
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_log_to_str
from langchain.agents.output_parsers import (
    ReActJsonSingleInputOutputParser,
)

from dotenv import load_dotenv
load_dotenv("env_keys")

from aux_tools import render_text_description_and_nested_args
from mm_tools import ( CharsList_Input2, llm_alibi_Input2, llm_chain_gen_chars, llm_chars_expand, llm_motiv_Input2, llm_secret_Input, llm_secret_Input2, victim_llm,
                        llm_secret, llm_murder, llm_alibi, llm_motiv)
from mm_tools import llm_chain_gen_chars_Input2, llm_murder_Input2, chars_expand_llm_Input2
# %%
llm = ChatNVIDIA(model="mistralai/mixtral-8x7b-instruct-v0.1")


tools=[
    StructuredTool.from_function(func=llm_murder.invoke,
                    name="murder_tool",
                    args_schema=llm_murder_Input2,
                    infer_schema=False,
                    description="""for a mistery murder game describe circustances and the crime scene 
                    output: the circustances"""
    ),
    StructuredTool.from_function(func=llm_chain_gen_chars.invoke,
                                 name="Generate_characterset_tool", 
                                 args_schema=llm_chain_gen_chars_Input2,
                                 description = "Gereate a first set of characters. Output is the description of the characters"
    ),
    StructuredTool.from_function(func=llm_chars_expand.invoke,
                                 name="expand_char_bio_tool",
                                 args_schema=chars_expand_llm_Input2,
                                 description="Useful when you want to generate a long bio for a character. output a long description of the character"
    ),
    StructuredTool.from_function(func=victim_llm.invoke,
                                    name="victim_tool",
                                    args_schema=CharsList_Input2,
                                    description="Useful when you want to generate a victim for a mistery muder game with a set of characters. Output is the description of the victim"
    ),
    StructuredTool.from_function(func=llm_motiv.invoke,
                                    name="motive_tool",
                                    args_schema=llm_motiv_Input2,
                                    description="""Useful when you want to genera a motive for a killing vicitim in a mystery murder game. 
                                                 Output is the motive of the character to be a posbile murderer"""
    ),
    StructuredTool.from_function(func=llm_secret.invoke,
                                 name="secret_tool",
                                 args_schema=llm_secret_Input2,
                                 description="Useful when you want to generate a secret related to the murder of a victim in a mystery murder game. Output is the generated secret."
    ),
    StructuredTool.from_function(func=llm_alibi.invoke,
                                 name="alibi_tool",
                                 args_schema=llm_alibi_Input2,
                                 description="Useful when you want to generate an alibi for a character. Output is the generated alib."
    ),
    
    ]



# %%
# setup tools
#tools = load_tools(["llm-math",], llm=llm)

# setup ReAct style prompt
prompt = hub.pull("hwchase17/react-json")
prompt = prompt.partial(
    tools=render_text_description_and_nested_args(tools),
    tool_names=", ".join([t.name for t in tools]),
)
print(prompt)
# define the agent
chat_model_with_stop = llm.bind(stop=["\nObservation"])
agent = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_log_to_str(x["intermediate_steps"]),
    }
    | prompt
    | chat_model_with_stop
    | ReActJsonSingleInputOutputParser()
)

# instantiate AgentExecutor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

agent_executor.invoke(
    {
        "input": "write mistery murder story for 5 people."
    }
)

# %%
from langchain.tools.render import render_text_description_and_args

tool_input = render_text_description_and_args(tools)
print(tool_input.replace("input: 'Input', config: 'Optional[RunnableConfig]' = None, **kwargs: 'Any'", ""))
# %%
print(str(llm_chain_gen_chars_Input2.schema_json()))
# %%

# %%
tool_input = render_text_description_and_nested_args(tools)
print(tool_input)
# %%
