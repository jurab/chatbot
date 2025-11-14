# schemas.py
from datetime import datetime
from typing import Literal, List

from pydantic import BaseModel


class MessageBase(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # pydantic v2; use orm_mode=True for v1


class ConversationCreate(BaseModel):
    # placeholder for future fields, rn we don't need anything
    pass


class ConversationRead(BaseModel):
    id: int
    created_at: datetime
    messages: List[MessageRead] = []

    class Config:
        from_attributes = True  # orm_mode=True on pydantic v1
