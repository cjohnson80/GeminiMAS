import os
import sys
import json
import asyncio
import logging
import psutil
import time
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from fastapi.responses import StreamingResponse

# Add parent dir to sys.path to import atlas_core
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from atlas_core import AtlasSwarm, read_local_config, WORKSPACE, heartbeat_daemon

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

atlas = AtlasSwarm(api_key)

# Active WebSocket connections
active_connections: List[WebSocket] = []

async def broadcast_telemetry():
    """Background task to push system health to all connected clients."""
    while True:
        if active_connections:
            try:
                stats = {
                    "type": "telemetry",
                    "cpu": psutil.cpu_percent(),
                    "ram": psutil.virtual_memory().percent,
                    "disk": psutil.disk_usage('/').percent,
                    "timestamp": time.time()
                }
                # Broadcast to all
                disconnected = []
                for connection in active_connections:
                    try:
                        await connection.send_json(stats)
                    except:
                        disconnected.append(connection)
                
                for conn in disconnected:
                    if conn in active_connections:
                        active_connections.remove(conn)
            except Exception as e:
                print(f"Telemetry error: {e}")
                    
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    # Run the heartbeat daemon in a separate thread
    threading.Thread(target=heartbeat_daemon, args=(api_key,), daemon=True).start()
    
    # Start telemetry broadcaster
    asyncio.create_task(broadcast_telemetry())
    print("[+] Atlas Background Heartbeat and Telemetry Broadcaster initiated.")

class ChatRequest(BaseModel):
    message: str
    project: Optional[str] = None
    audio_path: Optional[str] = None
    image_path: Optional[str] = None

@app.post("/prompt")
async def process_prompt(req: ChatRequest):
    """Synchronous prompt processing (returns generator for streaming)."""
    if req.project:
        atlas.current_project = req.project
    
    images = [req.image_path] if req.image_path else None
    
    async def stream_result():
        for update in atlas.process(req.message, stream=True, audio=req.audio_path, images=images):
            yield json.dumps(update) + "\n"
            
    return StreamingResponse(stream_result(), media_type="application/x-ndjson")

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
        pass

@app.post("/webhook/feedback")
async def receive_feedback(feedback: ClientFeedback, background_tasks: BackgroundTasks):
    """Endpoint for the Client Review Portal to submit UI feedback directly to Atlas."""
    background_tasks.add_task(trigger_atlas_feedback_task, feedback)
    return {"status": "Feedback received. Atlas is processing the request."}

@app.post("/voice")
async def upload_voice_command(project: str, file: UploadFile = File(...)):
    """Receives an audio file, saves it, and passes it to Atlas."""
    os.makedirs(os.path.join(WORKSPACE, project, "audio_inbox"), exist_ok=True)
    audio_path = os.path.join(WORKSPACE, project, "audio_inbox", f"cmd_{int(time.time())}_{file.filename}")
    
    with open(audio_path, "wb") as f:
        f.write(await file.read())
        
    return {"status": "Audio saved", "audio_path": audio_path}

@app.post("/abort")
async def abort_mission():
    """Emergency Stop: Signals Atlas to terminate the current task immediately."""
    atlas.status = "ABORTED"
    # We can also kill child processes if necessary
    return {"status": "ABORT_SIGNAL_SENT", "msg": "Atlas Swarm is terminating active mission."}

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
    active_connections.append(websocket)
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
        if websocket in active_connections:
            active_connections.remove(websocket)
        print("Client disconnected")
    except Exception as e:
        print(f"WS Error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)
        try:
            await websocket.send_json({"type": "error", "msg": str(e)})
        except: pass

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
