from collections.abc import Iterable
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def create_model(model: T, params: Iterable) -> T:
    return model(**dict(zip(model.__annotations__.keys(), params, strict=False)))
