from typing import Literal, List, Any
from pydantic import BaseModel


class MediaEvent(BaseModel):
    type: Literal["media"] = "media"
    media: List[Any]
