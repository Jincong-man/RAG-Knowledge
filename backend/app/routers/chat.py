"""聊天路由：问答SSE流式输出 + 会话管理"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db, async_session_factory
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationCreate, ConversationUpdate, ConversationOut,
    ChatRequest, ConversationWithMessages, MessageOut,
)
from app.core.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["聊天问答"])


# ==================== 会话管理 ====================

@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新会话"""
    conv = Conversation(user_id=current_user.id, title=data.title)
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有会话"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/conversations/{conv_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个会话及其所有消息"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
        .options(selectinload(Conversation.messages))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conv


@router.put("/conversations/{conv_id}", response_model=ConversationOut)
async def update_conversation(
    conv_id: int,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新会话标题"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    conv.title = data.title
    db.add(conv)
    return conv


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_200_OK)
async def delete_conversation(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除会话及其所有消息"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    await db.delete(conv)
    return {"message": "会话已删除"}


# ==================== 问答SSE ====================

@router.post("/stream")
async def chat_stream(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """SSE流式问答接口"""
    async def event_generator():
        try:
            # 1. 验证会话属于当前用户
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Conversation)
                    .where(
                        Conversation.id == data.conversation_id,
                        Conversation.user_id == current_user.id,
                    )
                )
                conv = result.scalar_one_or_none()
                if not conv:
                    yield f"event: error\ndata: {json.dumps({'error': '会话不存在'})}\n\n"
                    return

                # 2. 保存用户消息
                user_msg = Message(
                    conversation_id=data.conversation_id,
                    role="user",
                    content=data.message,
                )
                db.add(user_msg)

                # 3. 加载历史消息用于上下文
                history_result = await db.execute(
                    select(Message)
                    .where(Message.conversation_id == data.conversation_id)
                    .order_by(Message.created_at)
                )
                history = history_result.scalars().all()
                chat_history = [
                    {"role": msg.role, "content": msg.content} for msg in history[-20:]
                ]

                await db.commit()

            # 4. 调用RAG服务（流式）
            from app.services.rag_service import stream_rag_answer
            full_answer = ""
            references = []

            async for event in stream_rag_answer(data.message, chat_history):
                if event["type"] == "sources":
                    references = event["data"]
                    yield f"event: sources\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                elif event["type"] == "token":
                    full_answer += event["data"]
                    yield f"event: token\ndata: {json.dumps({'token': event['data']})}\n\n"
                elif event["type"] == "error":
                    yield f"event: error\ndata: {json.dumps({'error': event['data']})}\n\n"
                    return

            # 5. 保存AI回复
            async with async_session_factory() as db:
                ai_msg = Message(
                    conversation_id=data.conversation_id,
                    role="assistant",
                    content=full_answer,
                    referenced_docs=references if references else None,
                )
                db.add(ai_msg)

                # 更新会话标题（如果是第一条消息）
                if len(history) <= 1:
                    result = await db.execute(
                        select(Conversation).where(Conversation.id == data.conversation_id)
                    )
                    conv = result.scalar_one_or_none()
                    if conv and conv.title == "新对话":
                        conv.title = data.message[:50]
                        db.add(conv)

                await db.commit()

            yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logger.error(f"问答流式输出异常: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
