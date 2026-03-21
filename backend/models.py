from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class DebateMode(str, Enum):
    DEBATE = "debate"
    SITUATION = "situation"


class PersonalityMode(str, Enum):
    ACADEMIC = "academic"
    AGGRESSIVE = "aggressive"
    FRIENDLY = "friendly"
    PHILOSOPHICAL = "philosophical"
    BALANCED = "balanced"


class ClarifyRequest(BaseModel):
    topic: str = Field(..., min_length=5, max_length=1500, description="The rough situation to clarify")
    personality: PersonalityMode = Field(default=PersonalityMode.BALANCED)

class DebateRequest(BaseModel):
    topic: str = Field(..., min_length=5, max_length=1000, description="The debate topic or situation to analyze")
    mode: DebateMode = Field(default=DebateMode.DEBATE, description="Debate or Situation analysis mode")
    rounds: int = Field(default=4, ge=2, le=6, description="Number of debate rounds")
    personality: PersonalityMode = Field(default=PersonalityMode.BALANCED, description="Agent personality style")


class AgentMessage(BaseModel):
    agent: str
    role: str
    round: int
    round_label: str
    content: str
    icon: str
    color: str


class DebateStreamEvent(BaseModel):
    type: Literal["agent_start", "agent_chunk", "agent_end", "debate_end", "error"]
    agent: Optional[str] = None
    role: Optional[str] = None
    round: Optional[int] = None
    round_label: Optional[str] = None
    chunk: Optional[str] = None
    content: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    message: Optional[str] = None
    final_summary: Optional[dict] = None
