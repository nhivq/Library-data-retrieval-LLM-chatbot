from pydantic import BaseModel, Field

class AgentStep(BaseModel):
    """One tool execution step reported back to the streaming frontend."""

    step: int
    tool: str
    arguments: dict = Field(default_factory=dict)
    summary: str
    duration_ms: int
    status: str

class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""

    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Non-streaming response shape kept for compatibility/documentation."""

    answer: str
    progress: list[AgentStep] = Field(default_factory=list)
