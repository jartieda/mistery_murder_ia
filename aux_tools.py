import json
from typing import List, Dict, Any, Optional
from langchain.tools import StructuredTool, BaseTool

MAX_TRIES = 100

def replace_value_in_dict(item, original_schema):
    if isinstance(item, list):
        return [replace_value_in_dict(i, original_schema) for i in item]
    elif isinstance(item, dict):
        if list(item.keys()) == ['$ref']:
            definitions = item['$ref'][2:].split('/')
            res = original_schema.copy()
            for definition in definitions:
                res = res[definition]
            return res
        else:
            return { key: replace_value_in_dict(i, original_schema) for key, i in item.items()}
    else:
        return item

        

def recursive_replace(input_pydantic):
    schema = input_pydantic.schema()
    for i in range(MAX_TRIES):
        if '$ref' not in json.dumps(schema):
            break
        schema = replace_value_in_dict(schema.copy(), schema.copy())
    if 'definitions' in schema:
        del schema['definitions']

    return json.dumps(schema, indent=2)

# %%
def render_text_description_and_nested_args(tools: List[BaseTool]) -> str:
    """Render the tool name, description, and args (nested) in plain text.

    Output will be in the format of:

    .. code-block:: markdown

        search: This tool is used for search, args: {"query": {"type": "string"}}
        calculator: This tool is used for math, \
args: {"expression": {"type": "string"}}
    """
    tool_strings = []
    for tool in tools:
        args_schema = recursive_replace(tool.args_schema)
        description = f"{tool.name} - {tool.description}"
        tool_strings.append(f"{description}, args: {args_schema}")
    return "\n".join(tool_strings)
