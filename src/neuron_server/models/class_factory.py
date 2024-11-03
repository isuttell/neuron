from pydantic import BaseModel
from typing import Iterable, Callable
from typing import TypeVar

T = TypeVar("T", bound=BaseModel)


def create_model(model: T, params: Iterable) -> T:
    return model(**dict(zip(model.__annotations__.keys(), params)))
