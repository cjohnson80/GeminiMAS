import os
import importlib

class ToolBox:
    _tools = {}

    @classmethod
    def load_tools(cls):
        if cls._tools:
            return
        tools_dir = os.path.join(os.path.dirname(__file__), 'tools')
        for filename in os.listdir(tools_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module = importlib.import_module(f"tools.{module_name}")
                if hasattr(module, 'execute'):
                    cls._tools[module_name] = module.execute

    @classmethod
    def execute(cls, action, payload):
        try:
            cls.load_tools()
            if action in cls._tools:
                return cls._tools[action](payload)
            return "Unknown tool."
        except Exception as e:
            return f"Tool Error: {str(e)}"
