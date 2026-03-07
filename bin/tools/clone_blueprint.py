import os
import json
import shutil
import sys

def execute(payload):
    """
    Atlas Tool: Clones a foundational project blueprint into the target workspace.
    Payload: {
        "blueprint_name": "nextjs_saas_foundation",
        "target_dir": "workspace/my_new_project"
    }
    """
    try:
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload
            
        blueprint_name = data.get("blueprint_name")
        target_dir = data.get("target_dir")
        
        if not blueprint_name or not target_dir:
            return "Error: 'blueprint_name' and 'target_dir' are required."
            
        agent_root = os.path.expanduser("~/gemini_agents")
        source_dir = os.path.join(agent_root, "library", "blueprints", blueprint_name)
        target_full_path = os.path.join(agent_root, target_dir)
        
        if not os.path.exists(source_dir):
            # Try to list available blueprints to help the agent
            blueprints_dir = os.path.join(agent_root, "library", "blueprints")
            available = os.listdir(blueprints_dir) if os.path.exists(blueprints_dir) else []
            return f"Error: Blueprint '{blueprint_name}' not found. Available blueprints: {', '.join(available) if available else 'None'}"
            
        # Ensure target doesn't already exist or is empty
        if os.path.exists(target_full_path) and os.listdir(target_full_path):
            return f"Error: Target directory '{target_dir}' already exists and is not empty."
            
        shutil.copytree(source_dir, target_full_path, dirs_exist_ok=True)
        
        return f"Successfully cloned blueprint '{blueprint_name}' to '{target_dir}'. Ready for Modular Assembly."
        
    except Exception as e:
        return f"Blueprint Clone Error: {str(e)}"
