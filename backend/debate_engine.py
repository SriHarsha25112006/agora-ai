import json
import asyncio
from typing import AsyncGenerator, Optional
from backend.agents import AGENTS, call_agent_stream, call_agent_refine_stream


ROUND_LABELS = {
    1: "Round 1 — Core Perspectives",
    2: "Round 2 — Impact Perspectives",
    3: "Round 3 — Refinement",
    4: "Final Round — Consensus & Judgment",
}


def _agent_start_event(agent_key: str, round_num: int, name_override: str = None, role_override: str = None) -> dict:
    """Build a consistent agent_start event with model info included."""
    info = AGENTS[agent_key]
    return {
        "type": "agent_start",
        "agent": name_override or info["name"],
        "role": role_override or info["role"],
        "round": round_num,
        "round_label": ROUND_LABELS[round_num],
        "icon": info["icon"],
        "color": info["color"],
        "model_label": info["model_label"],
        "model_icon": info["model_icon"],
    }


async def run_debate_stream(
    topic: str,
    mode: str,
    personality: str,
) -> AsyncGenerator[str, None]:
    """
    Orchestrates the 4-round debate, streaming SSE-formatted JSON per agent.
    Each agent uses a different Ollama model (zero API keys).
    """

    def _event(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    # ── Storage ──────────────────────────────────────────────
    ethical_arg = ""
    legal_arg = ""
    economic_arg = ""
    social_arg = ""
    ethical_refined = ""
    legal_refined = ""

    # ── Round 1: Core Perspectives (Ethical, Legal) ──────────
    # Ethical Agent
    yield _event(_agent_start_event("ethical", 1))
    async for chunk in call_agent_stream("ethical", topic, mode, personality):
        ethical_arg += chunk
        yield _event({"type": "agent_chunk", "chunk": chunk})
    yield _event({"type": "agent_end", "agent": "ethical", "content": ethical_arg})
    await asyncio.sleep(0.2)

    # Legal Agent
    context_r1 = f"[ETHICAL PERSPECTIVE]\n{ethical_arg}"
    yield _event(_agent_start_event("legal", 1))
    async for chunk in call_agent_stream("legal", topic, mode, personality, context=context_r1):
        legal_arg += chunk
        yield _event({"type": "agent_chunk", "chunk": chunk})
    yield _event({"type": "agent_end", "agent": "legal", "content": legal_arg})
    await asyncio.sleep(0.2)

    # ── Round 2: Impact Perspectives (Economic, Social) ──────
    context_r2 = f"[ETHICAL PERSPECTIVE]\n{ethical_arg}\n\n[LEGAL PERSPECTIVE]\n{legal_arg}"

    # Economic Agent
    yield _event(_agent_start_event("economic", 2))
    async for chunk in call_agent_stream("economic", topic, mode, personality, context=context_r2):
        economic_arg += chunk
        yield _event({"type": "agent_chunk", "chunk": chunk})
    yield _event({"type": "agent_end", "agent": "economic", "content": economic_arg})
    await asyncio.sleep(0.2)

    # Social Agent
    context_r2b = context_r2 + f"\n\n[ECONOMIC PERSPECTIVE]\n{economic_arg}"
    yield _event(_agent_start_event("social", 2))
    async for chunk in call_agent_stream("social", topic, mode, personality, context=context_r2b):
        social_arg += chunk
        yield _event({"type": "agent_chunk", "chunk": chunk})
    yield _event({"type": "agent_end", "agent": "social", "content": social_arg})
    await asyncio.sleep(0.2)

    # ── Round 3: Refinement ──────────────────────────────────
    all_perspectives = f"""[ETHICAL] {ethical_arg}
[LEGAL] {legal_arg}
[ECONOMIC] {economic_arg}
[SOCIAL] {social_arg}"""

    # Ethical Agent Refined
    yield _event(_agent_start_event("ethical", 3, name_override="Ethical Agent (Refined)", role_override="Ethical Advocate — Refined"))
    async for chunk in call_agent_refine_stream(
        "ethical", topic, mode, personality,
        original_arg=ethical_arg, other_perspectives=all_perspectives,
    ):
        ethical_refined += chunk
        yield _event({"type": "agent_chunk", "chunk": chunk})
    yield _event({"type": "agent_end", "agent": "ethical_refined", "content": ethical_refined})
    await asyncio.sleep(0.2)

    # Legal Agent Refined
    yield _event(_agent_start_event("legal", 3, name_override="Legal Agent (Refined)", role_override="Legal Analyst — Refined"))
    async for chunk in call_agent_refine_stream(
        "legal", topic, mode, personality,
        original_arg=legal_arg, other_perspectives=all_perspectives,
    ):
        legal_refined += chunk
        yield _event({"type": "agent_chunk", "chunk": chunk})
    yield _event({"type": "agent_end", "agent": "legal_refined", "content": legal_refined})
    await asyncio.sleep(0.2)

    # ── Round 4: Final Consensus (Judge) ─────────────────────
    full_context = f"""[ETHICAL PERSPECTIVE — REFINED]
{ethical_refined}

[LEGAL PERSPECTIVE — REFINED]
{legal_refined}

[ECONOMIC PERSPECTIVE]
{economic_arg}

[SOCIAL PERSPECTIVE]
{social_arg}"""

    yield _event(_agent_start_event("consensus", 4))
    judge_output = ""
    async for chunk in call_agent_stream("consensus", topic, mode, personality, context=full_context):
        judge_output += chunk
        yield _event({"type": "agent_chunk", "chunk": chunk})
    yield _event({"type": "agent_end", "agent": "consensus", "content": judge_output})

    # ── Debate Complete ──────────────────────────────────────
    yield _event({
        "type": "debate_end",
        "message": "Debate complete.",
        "final_summary": {"topic": topic, "mode": mode, "total_rounds": 4},
    })
