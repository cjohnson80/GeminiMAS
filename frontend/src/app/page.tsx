"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Send, 
  Bot, 
  User, 
  Terminal, 
  Activity, 
  Folder, 
  Cpu, 
  Zap,
  ChevronRight,
  BrainCircuit,
  Settings,
  Plus,
  Mic,
  MicOff,
  Radio,
  MessageSquare
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface Message {
  id: string;
  role: "user" | "atlas";
  content: string;
  thoughts?: string[];
  actions?: Array<{ tool: string; payload: string }>;
  status?: string;
  completed?: boolean;
}

export default function AtlasControl() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [currentProject, setCurrentProject] = useState("default");
  const [projects, setProjects] = useState<string[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  
  // Voice State
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initial fetch
    fetchProjects();
    fetchStatus();
    
    // Setup WebSocket
    const socket = new WebSocket("ws://localhost:8000/ws/chat");
    
    socket.onopen = () => {
      console.log("Atlas Connected");
      setWs(socket);
    };
    
    socket.onmessage = (event) => {
      const update = JSON.parse(event.data);
      handleSwarmUpdate(update);
    };
    
    socket.onclose = () => {
      console.log("Atlas Disconnected");
      setWs(null);
    };

    return () => socket.close();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const fetchProjects = async () => {
    try {
      const res = await fetch("http://localhost:8000/projects");
      const data = await res.json();
      setProjects(data);
    } catch (e) { console.error(e); }
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch("http://localhost:8000/status");
      const data = await res.json();
      setSystemStatus(data);
    } catch (e) { console.error(e); }
  };

  const handleSwarmUpdate = (update: any) => {
    setMessages(prev => {
      const lastMsg = prev[prev.length - 1];
      if (!lastMsg || lastMsg.role === "user" || lastMsg.completed) {
        const newMsg: Message = {
          id: Math.random().toString(36).substring(7),
          role: "atlas",
          content: "",
          thoughts: [],
          actions: [],
          completed: false
        };
        return [...prev, processUpdate(newMsg, update)];
      } else {
        const updated = [...prev];
        updated[updated.length - 1] = processUpdate({ ...lastMsg }, update);
        return updated;
      }
    });

    if (update.type === "final_answer") {
      setIsTyping(false);
    }
  };

  const processUpdate = (msg: Message, update: any) => {
    switch (update.type) {
      case "chunk":
        msg.content += update.msg;
        break;
      case "thought":
        msg.thoughts = [...(msg.thoughts || []), update.msg];
        break;
      case "action":
        msg.actions = [...(msg.actions || []), { tool: update.tool, payload: update.payload }];
        break;
      case "status":
        msg.status = update.msg;
        break;
      case "final_answer":
        msg.content = update.msg;
        msg.completed = true;
        break;
    }
    return msg;
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunks.current = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };
      
      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks.current, { type: "audio/webm" });
        await uploadVoice(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const uploadVoice = async (blob: Blob) => {
    const formData = new FormData();
    formData.append("file", blob, "voice_command.webm");
    
    setIsTyping(true);
    try {
      const res = await fetch(`http://localhost:8000/voice?project=${currentProject}`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      
      if (ws) {
        ws.send(JSON.stringify({ 
          message: "[VOICE COMMAND ATTACHED]", 
          project: currentProject,
          audio_path: data.audio_path 
        }));
      }
    } catch (e) {
      console.error("Voice upload failed:", e);
      setIsTyping(false);
    }
  };

  const sendMessage = () => {
    if (!input.trim() || !ws) return;
    
    const userMsg: Message = {
      id: Math.random().toString(36).substring(7),
      role: "user",
      content: input,
      completed: true
    };
    
    setMessages(prev => [...prev, userMsg]);
    ws.send(JSON.stringify({ message: input, project: currentProject }));
    setInput("");
    setIsTyping(true);
  };

  const submitFeedback = async () => {
    const feedback = prompt("Enter client feedback for this mission:");
    if (!feedback) return;
    
    try {
      await fetch("http://localhost:8000/webhook/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project: currentProject,
          feedback_text: feedback,
          url: "http://localhost:3000"
        })
      });
      alert("Feedback transmitted to Atlas Swarm.");
    } catch (e) { console.error(e); }
  };

  return (
    <div className="flex h-screen w-full bg-[#0a0a0a] overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-800 flex flex-col bg-[#0d0d0d]">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight text-white">ATLAS</span>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-2 px-2">Projects</div>
            <button className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-zinc-800 transition-colors text-zinc-300 text-sm mb-1 border border-dashed border-zinc-700">
              <Plus className="w-4 h-4" /> New Project
            </button>
            {projects.map(p => (
              <button 
                key={p}
                onClick={() => setCurrentProject(p)}
                className={cn(
                  "w-full flex items-center gap-2 px-2 py-1.5 rounded-md transition-colors text-sm mb-1",
                  currentProject === p ? "bg-blue-600/10 text-blue-400 border border-blue-600/20" : "text-zinc-400 hover:bg-zinc-800"
                )}
              >
                <Folder className="w-4 h-4" /> {p}
              </button>
            ))}
          </div>

          <div className="pt-4">
            <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-2 px-2">Operator Tools</div>
            <button 
              onClick={submitFeedback}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-zinc-800 transition-colors text-zinc-400 text-sm"
            >
              <MessageSquare className="w-4 h-4" /> Submit Feedback
            </button>
          </div>
        </div>

        {/* System Stats Footer */}
        <div className="p-4 border-t border-zinc-800 bg-[#0a0a0a] space-y-2">
          <div className="flex items-center justify-between text-[10px] font-medium">
            <span className="text-zinc-500 flex items-center gap-1.5"><Cpu className="w-3 h-3" /> CPU Load</span>
            <span className="text-green-500">{systemStatus?.hardware?.cpu_count || 0} Cores</span>
          </div>
          <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 w-[15%]" />
          </div>
          <div className="flex items-center justify-between text-[10px] font-medium pt-1">
            <span className="text-zinc-500 flex items-center gap-1.5"><Activity className="w-3 h-3" /> Status</span>
            <span className="text-blue-400 uppercase tracking-tighter">Ready</span>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col relative bg-[#0a0a0a]">
        <header className="h-14 border-b border-zinc-800 flex items-center justify-between px-6 bg-[#0a0a0a]/80 backdrop-blur-sm z-10">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 text-xs font-medium text-zinc-500">
              <span>Workspace</span>
              <ChevronRight className="w-3 h-3" />
              <span className="text-zinc-300 bg-zinc-800 px-2 py-0.5 rounded uppercase">{currentProject}</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button className="text-zinc-400 hover:text-white transition-colors"><Settings className="w-5 h-5" /></button>
          </div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-8 space-y-8 scroll-smooth">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4">
              <div className="w-16 h-16 bg-zinc-900 border border-zinc-800 rounded-2xl flex items-center justify-center mb-4">
                <BrainCircuit className="w-8 h-8 text-blue-500" />
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">Welcome to Atlas Control</h2>
              <p className="text-zinc-400 text-sm leading-relaxed">
                Atlas is currently synchronized with the swarm. Direct the agency to begin autonomous operations or research via text or voice.
              </p>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.id} className={cn("max-w-3xl mx-auto flex gap-4", m.role === "user" ? "justify-end" : "justify-start")}>
              {m.role === "atlas" && (
                <div className="w-8 h-8 rounded-lg bg-blue-600 flex-shrink-0 flex items-center justify-center mt-1">
                  <Bot className="w-5 h-5 text-white" />
                </div>
              )}
              
              <div className={cn("flex flex-col space-y-3 max-w-[90%]", m.role === "user" ? "items-end" : "items-start")}>
                <div className={cn(
                  "p-4 rounded-2xl text-sm leading-relaxed",
                  m.role === "user" ? "bg-zinc-800 text-white" : "bg-transparent text-zinc-200 border border-transparent"
                )}>
                  {m.role === "atlas" ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                      {!m.completed && !m.content && (
                        <div className="flex gap-1 items-center py-2">
                          <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" />
                          <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce [animation-delay:0.2s]" />
                          <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce [animation-delay:0.4s]" />
                        </div>
                      )}
                    </div>
                  ) : (
                    m.content
                  )}
                </div>

                {/* Sub-steps / Thoughts / Actions */}
                {m.role === "atlas" && (
                  <div className="space-y-2 w-full">
                    {m.thoughts?.map((t, i) => (
                      <div key={i} className="flex items-start gap-2 bg-yellow-500/5 border border-yellow-500/10 p-3 rounded-xl">
                        <div className="mt-0.5"><BrainCircuit className="w-3.5 h-3.5 text-yellow-500/60" /></div>
                        <p className="text-[12px] text-yellow-200/70 italic leading-snug">{t}</p>
                      </div>
                    ))}
                    {m.actions?.map((a, i) => (
                      <div key={i} className="flex items-center gap-2 bg-blue-500/5 border border-blue-500/10 px-3 py-2 rounded-xl">
                        <Terminal className="w-3.5 h-3.5 text-blue-500/60" />
                        <div className="flex gap-2 text-[11px] font-mono">
                          <span className="text-blue-400 font-bold uppercase">{a.tool}</span>
                          <span className="text-zinc-500 truncate max-w-[200px]">{a.payload}</span>
                        </div>
                      </div>
                    ))}
                    {m.status && !m.completed && (
                      <div className="flex items-center gap-2 px-3 text-[11px] text-zinc-500 font-medium">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
                        {m.status}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {m.role === "user" && (
                <div className="w-8 h-8 rounded-lg bg-zinc-800 flex-shrink-0 flex items-center justify-center mt-1">
                  <User className="w-5 h-5 text-zinc-400" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="p-6 bg-gradient-to-t from-[#0a0a0a] via-[#0a0a0a] to-transparent">
          <div className="max-w-3xl mx-auto relative flex items-end gap-2">
            <div className="relative flex-1">
              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder={isRecording ? "Listening to Mission Commander..." : "Command Atlas swarm..."}
                className={cn(
                  "w-full bg-[#121212] border border-zinc-800 rounded-2xl py-4 pl-4 pr-12 text-sm focus:outline-none focus:border-blue-600/50 transition-all resize-none placeholder:text-zinc-600",
                  isRecording && "border-red-500/50 bg-red-500/5 ring-1 ring-red-500/20"
                )}
              />
              
              {isRecording && (
                <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                  <Radio className="w-4 h-4 text-red-500 animate-pulse" />
                </div>
              )}
            </div>

            <div className="flex gap-2 mb-1">
              <button 
                onClick={isRecording ? stopRecording : startRecording}
                className={cn(
                  "p-3 rounded-xl transition-all",
                  isRecording 
                    ? "bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/20" 
                    : "bg-zinc-800 hover:bg-zinc-700 text-zinc-400"
                )}
              >
                {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>

              <button 
                onClick={sendMessage}
                disabled={!input.trim() || !ws || isRecording}
                className="p-3 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 rounded-xl transition-all shadow-lg shadow-blue-600/20"
              >
                <Send className="w-5 h-5 text-white" />
              </button>
            </div>
          </div>
          <p className="text-[10px] text-zinc-600 text-center mt-3 tracking-tight">
            ATLAS V9.0 ELITE | AUDIO COMMAND CHANNEL ACTIVE | AUTONOMOUS SWARM ENABLED
          </p>
        </div>
      </main>
    </div>
  );
}
