import os
import sys
import json
import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import time

# Add parent dir to sys.path to import gemini_mas
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gemini_mas import GeminiMAS, read_local_config, WORKSPACE

app = FastAPI(title="Atlas API Gateway")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Atlas Instance
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL: GEMINI_API_KEY not set!")
    sys.exit(1)

atlas = GeminiMAS(api_key)

class ChatRequest(BaseModel):
    message: str
    project: Optional[str] = None

class ClientFeedback(BaseModel):
    project: str
    component_id: Optional[str] = None
    url: Optional[str] = None
    feedback_text: str

def trigger_atlas_feedback_task(feedback: ClientFeedback):
    # This runs in the background to process feedback
    prompt = f"CLIENT FEEDBACK RECEIVED for {feedback.project} on {feedback.url}.\nComponent: {feedback.component_id}\nFeedback: {feedback.feedback_text}\n\nInitiate the SRE or Developer protocol to find the relevant code and apply the requested changes immediately."
    atlas.current_project = feedback.project
    for _ in atlas.process(prompt, stream=True):
        pass # The result is saved to the workspace/logs natively

@app.post("/webhook/feedback")
async def receive_feedback(feedback: ClientFeedback, background_tasks: BackgroundTasks):
    """Endpoint for the Client Review Portal to submit UI feedback directly to Atlas."""
    background_tasks.add_task(trigger_atlas_feedback_task, feedback)
    return {"status": "Feedback received. Atlas is processing the request."}

@app.post("/voice")
async def upload_voice_command(project: str, file: UploadFile = File(...)):
    """Receives an audio file (e.g., from the web dashboard), saves it, and passes it to Atlas."""
    os.makedirs(os.path.join(WORKSPACE, project, "audio_inbox"), exist_ok=True)
    audio_path = os.path.join(WORKSPACE, project, "audio_inbox", f"cmd_{int(time.time())}_{file.filename}")
    
    with open(audio_path, "wb") as f:
        f.write(await file.read())
        
    # We will trigger Atlas via the websocket or a background task, 
    # but for now, we just save it and return the path so the frontend can send a chat message referencing it.
    return {"status": "Audio saved", "audio_path": audio_path}

@app.get("/status")
async def get_status():
    cfg = read_local_config()
    hw = cfg.get("_current_probe", {})
    return {
        "machine": atlas.machine_name,
        "project": atlas.current_project,
        "hardware": hw,
        "status": "online"
    }

@app.get("/projects")
async def list_projects():
    if not os.path.exists(WORKSPACE):
        return []
    projects = [p for p in os.listdir(WORKSPACE) if os.path.isdir(os.path.join(WORKSPACE, p))]
    return projects

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            prompt = req.get("message")
            project = req.get("project")
            audio_path = req.get("audio_path")
            
            if project:
                atlas.current_project = project
            
            # Use the generator-based process method with audio support
            for update in atlas.process(prompt, stream=True, audio=audio_path):
                await websocket.send_json(update)
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WS Error: {e}")
        try:
            await websocket.send_json({"type": "error", "msg": str(e)})
        except: pass

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
