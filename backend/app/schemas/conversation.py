"""对话和消息相关的Pydantic模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)


class ConversationUpdate(BaseModel):
    title: str = Field(..., max_length=200)


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReferencedDoc(BaseModel):
    filename: str
    chunk_index: int
    content: str
    score: float


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    referenced_docs: Optional[list[ReferencedDoc]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    conversation_id: int = Field(..., description="会话ID")
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")


class ConversationWithMessages(ConversationOut):
    messages: list[MessageOut] = []
