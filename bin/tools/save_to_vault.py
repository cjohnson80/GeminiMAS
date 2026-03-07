import os
import json
import sys

# To allow importing from parent bin dir if needed, but we'll try to keep it simple
# Dynamic tools are executed within the context of atlas_core usually

def execute(payload):
    """
    Atlas Tool: Saves a component to the NextStep Component Vault.
    Payload: {
        "name": "HeroSection",
        "category": "UI",
        "description": "Modern dark hero with gradient text",
        "content": "export default function Hero() { ... }",
        "tags": "nextjs, tailwind, hero"
    }
    """
    try:
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload
            
        name = data.get("name")
        category = data.get("category", "General")
        description = data.get("description", "")
        content = data.get("content", "")
        tags = data.get("tags", "")
        
        if not name or not content:
            return "Error: Name and content are required."
            
        # Define storage path
        safe_name = name.lower().replace(" ", "_")
        dir_path = os.path.join("library/components", category.lower())
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f"{safe_name}.tsx")
        
        # Save file
        with open(file_path, "w") as f:
            f.write(content)
            
        # Metadata for DB (this will be handled by the core engine calling the DB method)
        # However, a dynamic tool doesn't have direct DB access easily unless passed.
        # So we return a success message and instructions for the engine.
        
        return {
            "status": "success",
            "msg": f"Component '{name}' written to {file_path}",
            "db_action": "save_component",
            "db_params": {
                "name": name,
                "category": category,
                "description": description,
                "file_path": file_path,
                "tags": tags
            }
        }
    except Exception as e:
        return f"Error in save_to_vault: {str(e)}"
