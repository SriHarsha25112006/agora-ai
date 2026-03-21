# Dialectica AI 🧠⚖️

**Multi-Agent Reasoning & Debate Engine**

Dialectica AI orchestrates 5 specialized AI agents across 4 structured debate rounds to analyze any topic, dilemma, or ethical question — and converge on a well-reasoned conclusion.

## Agents

| Agent | Role | Color |
|-------|------|-------|
| ⚡ Pro Agent | Advocates the affirmative | Teal |
| 🔥 Con Agent | Opposes with counterarguments | Red |
| 🔍 Critic Agent | Audits both sides for logical flaws | Gold |
| 📊 Research Agent | Grounds debate in facts & data | Violet |
| ⚖️ Judge Agent | Delivers the final verdict | White |

## Quick Start

### 1. Prerequisites
- Python 3.10+
- A free [Groq API Key](https://console.groq.com)

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API key
```bash
# Copy the template and fill in your key
copy .env.example .env
# Open .env and set: GROQ_API_KEY=gsk_...
```

### 4. Start the backend
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 5. Open the frontend
Open `frontend/index.html` in your browser — or serve it:
```bash
cd frontend
python -m http.server 3000
# Then open http://localhost:3000
```

## Modes

- **Debate Mode** — Classic pro/con structured debate on any topic
- **Situation Analysis** — Analyzes a personal or professional dilemma from multiple expert lenses

## Debate Structure

```
Round 1 │ Pro & Con  → Initial arguments
Round 2 │ Critic & Research → Analysis + factual grounding
Round 3 │ Pro & Con  → Refined arguments
Round 4 │ Judge      → Final verdict & recommendation
```

## Personality Modes

| Mode | Style |
|------|-------|
| Balanced | Clear, measured, rational |
| Academic | Formal, citation-aware |
| Aggressive | Bold, assertive, confrontational |
| Friendly | Warm, relatable, empathetic |
| Philosophical | Abstract, principle-driven |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · FastAPI · SSE |
| LLM | Groq · Llama 3 70B |
| Frontend | HTML · CSS · Vanilla JS |
| Streaming | Server-Sent Events |

## Project Structure

```
Dialectica AI/
├── backend/
│   ├── agents.py         # 5 agent definitions + Groq streaming
│   ├── debate_engine.py  # 4-round orchestration
│   ├── main.py           # FastAPI app
│   └── models.py         # Pydantic models
├── frontend/
│   ├── index.html        # App shell
│   ├── style.css         # Dark glassmorphism UI
│   └── app.js            # SSE client + rendering
├── requirements.txt
├── .env.example
└── README.md
```
