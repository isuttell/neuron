from pydantic import BaseModel
from typing import Optional


class StreamEvent(BaseModel):
    prompt: str
    thread_id: str
    personality_id: Optional[str]
    user_id: str
    username: str
