from pydantic import BaseModel


class StreamEvent(BaseModel):
    prompt: str
    thread_id: str
    personality_id: str | None
    user_id: str
    username: str
