import asyncio
import os
import yaml
from typing import AsyncGenerator

# ============================================================
# Local Ollama client setup
# ============================================================
from ollama import AsyncClient as OllamaAsyncClient
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ollama_client = OllamaAsyncClient(host=OLLAMA_HOST)

# ============================================================
# Cloud Groq API Setup (Fallback)
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None
if GROQ_API_KEY:
    try:
        from groq import AsyncGroq
        groq_client = AsyncGroq(api_key=GROQ_API_KEY)
    except ImportError:
        pass

# Groq Model Mappings
GROQ_MODELS = {
    "ethical": "gemma2-9b-it",
    "legal": "llama-3.3-70b-versatile",
    "economic": "llama-3.1-8b-instant",
    "social": "mixtral-8x7b-32768",
    "consensus": "llama3-70b-8192",
    "clarifier": "llama-3.1-8b-instant",
}

# ============================================================
# Agent configurations
# ============================================================
AGENTS = {
    "ethical": {
        "name": "Ethical Agent",
        "role": "Ethical Advocate",
        "icon": "⚖️",
        "color": "#00d4aa",
        "short": "ETHICAL",
        "model": "gemma2:2b",
        "model_label": "Gemma 2 · Google",
        "model_icon": "🔷",
    },
    "legal": {
        "name": "Legal Agent",
        "role": "Legal Analyst",
        "icon": "📜",
        "color": "#ff6b6b",
        "short": "LEGAL",
        "model": "llama3.2:3b",
        "model_label": "Llama 3.2 · Meta",
        "model_icon": "🦙",
    },
    "economic": {
        "name": "Economic Agent",
        "role": "Economic Forecaster",
        "icon": "📈",
        "color": "#ffd166",
        "short": "ECONOMIC",
        "model": "qwen2.5:3b",
        "model_label": "Qwen 2.5 · Alibaba",
        "model_icon": "🌸",
    },
    "social": {
        "name": "Social Impact Agent",
        "role": "Social Assessor",
        "icon": "🤝",
        "color": "#6c63ff",
        "short": "SOCIAL",
        "model": "mistral:latest",
        "model_label": "Mistral 7B · Mistral AI",
        "model_icon": "🌪️",
    },
    "consensus": {
        "name": "Consensus Agent",
        "role": "Consensus Builder",
        "icon": "🏛️",
        "color": "#f8f8f2",
        "short": "CONSENSUS",
        "model": "phi3.5:mini",
        "model_label": "Phi-3.5 Mini · Microsoft",
        "model_icon": "🔬",
    },
    "clarifier": {
        "name": "Clarifier Agent",
        "role": "Moderator",
        "icon": "📝",
        "color": "#ffffff",
        "short": "CLARIFIER",
        "model": "qwen2.5:3b",
        "model_label": "Qwen 2.5 · Alibaba",
        "model_icon": "🌸",
    },
}

# ============================================================
# Load Prompts from YAML
# ============================================================
PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "prompts.yaml")
with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
    _PROMPT_CONFIG = yaml.safe_load(f)

def _build_system_prompt(agent_key: str, mode: str, personality: str) -> str:
    tone_desc = _PROMPT_CONFIG.get("tones", {}).get(personality, _PROMPT_CONFIG["tones"]["balanced"])
    mode_desc = _PROMPT_CONFIG.get("modes", {}).get(mode, _PROMPT_CONFIG["modes"]["debate"])
    
    raw_prompt = _PROMPT_CONFIG.get("agents", {}).get(agent_key, "You are a helpful AI.")
    return raw_prompt.replace("{mode_ctx}", mode_desc).replace("{tone}", tone_desc)


# ============================================================
# Build user message per agent type
# ============================================================
def _build_user_message(agent_key: str, topic: str, mode: str, context: str = "") -> str:
    base = f"Topic: {topic}"
    if context:
        base += f"\n\nDebate context so far:\n{context}"

    instructions = {
        "ethical": "\n\nPresent your argument from an ETHICAL standpoint.",
        "legal": "\n\nPresent your argument from a LEGAL and REGULATORY standpoint.",
        "economic": "\n\nPresent your argument from an ECONOMIC and FINANCIAL standpoint.",
        "social": "\n\nPresent your argument highlighting SOCIAL and COMMUNITY IMPACTS.",
        "consensus": "\n\nDeliver the FINAL CONSENSUS. Synthesize all perspectives into a definitive, balanced conclusion.",
        "clarifier": "\n\nRewrite the input above into a single, perfectly clear and objective scenario/dilemma statement. Do not answer it.",
    }
    return base + instructions[agent_key]


# ============================================================
# Streaming LLM call (Groq API or Ollama Local)
# ============================================================
async def call_agent_stream(
    agent_key: str,
    topic: str,
    mode: str,
    personality: str,
    context: str = "",
) -> AsyncGenerator[str, None]:
    """Stream response chunks from the agent's assigned model."""
    agent_info = AGENTS[agent_key]
    system_prompt = _build_system_prompt(agent_key, mode, personality)
    user_message = _build_user_message(agent_key, topic, mode, context)

    try:
        if groq_client:
            model_name = GROQ_MODELS.get(agent_key, "llama-3.1-8b-instant")
            stream = await groq_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                stream=True,
                temperature=0.75,
                max_tokens=650,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content if (chunk.choices and chunk.choices[0].delta.content) else ""
                if content:
                    yield content

        else:
            # Check available models and fallback if missing
            local_models = await ollama_client.list()
            available_names = [m["model"] for m in local_models.get("models", [])]
            model_name = agent_info["model"]
            
            if not any(model_name.split(":")[0] in a for a in available_names):
                model_name = available_names[0] if available_names else "llama3.2:3b"

            stream = await ollama_client.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                stream=True,
                options={"num_predict": 650, "temperature": 0.75, "top_p": 0.9},
            )
            async for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
    except Exception as e:
        yield f"\n\n[Agent Error: Could not connect or infer: {str(e)}]"


# ============================================================
# Refinement round
# ============================================================
async def call_agent_refine_stream(
    agent_key: str,
    topic: str,
    mode: str,
    personality: str,
    original_arg: str,
    other_perspectives: str,
) -> AsyncGenerator[str, None]:
    """Streaming refinement round with full debate context."""
    agent_info = AGENTS[agent_key]
    system_prompt = _build_system_prompt(agent_key, mode, personality)
    perspective_name = agent_info["role"]

    user_message = f"""Topic: {topic}

Your original argument ({perspective_name}):
{original_arg}

Other perspectives presented in the debate:
{other_perspectives}

Now REFINE your argument in light of the other perspectives. Address their concerns where relevant, strengthen your core thesis, and adapt your position to offer a more nuanced view."""

    try:
        if groq_client:
            model_name = GROQ_MODELS.get(agent_key, "llama-3.1-8b-instant")
            stream = await groq_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                stream=True,
                temperature=0.70,
                max_tokens=650,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
                if content:
                    yield content

        else:
            # Check available models and fallback if missing
            local_models = await ollama_client.list()
            available_names = [m["model"] for m in local_models.get("models", [])]
            model_name = agent_info["model"]
            
            if not any(model_name.split(":")[0] in a for a in available_names):
                model_name = available_names[0] if available_names else "llama3.2:3b"

            stream = await ollama_client.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                stream=True,
                options={"num_predict": 650, "temperature": 0.70, "top_p": 0.9},
            )
            async for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
    except Exception as e:
        yield f"\n\n[Agent Error: Could not connect or infer: {str(e)}]"
