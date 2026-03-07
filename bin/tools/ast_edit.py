import libcst as cst
import json
import os

class AddFunctionTransformer(cst.CSTTransformer):
    def __init__(self, func_code):
        self.func_node = cst.parse_statement(func_code)

    def leave_Module(self, original_node, updated_node):
        new_body = list(updated_node.body)
        new_body.append(self.func_node)
        return updated_node.with_changes(body=new_body)

def execute(payload):
    """
    Atlas Tool: Performs precise AST-based code modification.
    Payload: {
        "path": "bin/atlas_core.py",
        "action": "add_function",
        "code": "def new_feature():\n    pass"
    }
    """
    try:
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload
            
        file_path = data.get("path")
        action = data.get("action")
        code_to_inject = data.get("code")
        
        if not os.path.exists(file_path):
            return f"Error: File {file_path} not found."

        with open(file_path, "r") as f:
            source_code = f.read()

        module = cst.parse_module(source_code)
        
        if action == "add_function":
            transformer = AddFunctionTransformer(code_to_inject)
            modified_module = module.visit(transformer)
            
            with open(file_path, "w") as f:
                f.write(modified_module.code)
            return f"AST: Successfully injected function into {file_path}."
            
        return f"Error: Unknown AST action {action}"

    except Exception as e:
        return f"AST Error: {str(e)}"
