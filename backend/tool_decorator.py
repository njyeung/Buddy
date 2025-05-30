import inspect
from state import tool_definitions, tool_functions

def tool(description: str = None):
    def decorator(fn):
        sig = inspect.signature(fn)
        params_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for name, param in sig.parameters.items():
            hint = param.annotation
            default = param.default

            if hint != inspect.Parameter.empty:
                param_type = hint.__name__
            elif default != inspect.Parameter.empty:
                param_type = type(default).__name__
            else:
                param_type = "str"
            
            json_type = {
                "int": "integer",
                "float": "number",
                "str": "string",
                "bool": "boolean",
                "list": "array",
                "dict": "object"
            }.get(param_type, "string")
            
            # Build parameter schema
            param_schema = {"type": json_type}
            if default != inspect.Parameter.empty:
                param_schema["default"] = default
            params_schema["properties"][name] = param_schema

            if param.default == inspect.Parameter.empty:
                params_schema["required"].append(name)

        tool_def = {
            "type": "function",
            "function": {
                "name": fn.__name__,
                "description": description or fn.__doc__ or f"Autogenerated tool for {fn.__name__}",
                "parameters": params_schema
            }
        }

        tool_definitions.append(tool_def)
        tool_functions[fn.__name__] = fn
        return fn
    return decorator
