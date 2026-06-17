from pydantic import BaseModel, Field

class AgentStep(BaseModel):
    step: int
    tool: str
    arguments: dict = Field(default_factory=dict)
    summary: str
    duration_ms: int
    status: str

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    progress: list[AgentStep] = Field(default_factory=list)
