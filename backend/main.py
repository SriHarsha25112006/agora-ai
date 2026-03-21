import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from backend.models import DebateRequest, ClarifyRequest
from backend.debate_engine import run_debate_stream
from backend.agents import AGENTS, OLLAMA_HOST, call_agent_stream
from ollama import AsyncClient
import json

app = FastAPI(
    title="Agora AI",
    description="Multi-Agent Reasoning & Debate Engine — Powered by 5 local Ollama LLMs",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Required models for each agent
REQUIRED_MODELS = {agent: info["model"] for agent, info in AGENTS.items()}


@app.get("/api/health")
async def health():
    """Check Ollama availability and which required models are ready."""
    client = AsyncClient(host=OLLAMA_HOST)
    try:
        response = await client.list()
        available = {m.model for m in response.models}

        # Strip tags for partial matching (e.g. "mistral:latest" → "mistral")
        def is_available(model_name: str) -> bool:
            return any(
                model_name in a or a.startswith(model_name.split(":")[0])
                for a in available
            )

        model_status = {
            agent: {
                "model": info["model"],
                "label": info["model_label"],
                "ready": is_available(info["model"]),
            }
            for agent, info in AGENTS.items()
        }
        all_ready = all(s["ready"] for s in model_status.values())

        return {
            "status": "ok" if all_ready else "partial",
            "ollama": "connected",
            "models_ready": all_ready,
            "model_status": model_status,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama not reachable at {OLLAMA_HOST}. Is Ollama running? Install from https://ollama.com — then run: ollama serve"
        )


@app.post("/api/clarify")
async def clarify(request: ClarifyRequest):
    """Rewrite a vague situation into a clear scenario statement."""
    async def event_generator():
        yield f"data: {json.dumps({'type': 'agent_start', 'agent': 'Clarifier', 'role': 'Moderator'})}\n\n"
        output = ""
        try:
            async for chunk in call_agent_stream("clarifier", request.topic, "situation", request.personality.value):
                output += chunk
                yield f"data: {json.dumps({'type': 'agent_chunk', 'chunk': chunk})}\n\n"
        except Exception as e:
            output += f"\n\n[Error: {str(e)}]"
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'agent_end', 'agent': 'clarifier', 'content': output})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/debate")
async def debate(request: DebateRequest):
    """Start a multi-agent debate. Returns an SSE stream of agent events."""

    async def event_generator():
        async for event in run_debate_stream(
            topic=request.topic,
            mode=request.mode.value,
            personality=request.personality.value,
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=True)
