from typing import Any, Literal

from pydantic import BaseModel


class MediaEvent(BaseModel):
    type: Literal["media"] = "media"
    media: list[Any]
