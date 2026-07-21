"""会话管理模块测试：创建、列表、详情、删除"""
import pytest
from httpx import AsyncClient


class TestCreateConversation:
    """创建会话测试"""

    async def test_create_conversation_success(self, client: AsyncClient, user_headers):
        """测试正常创建会话"""
        resp = await client.post("/api/chat/conversations", headers=user_headers, json={
            "title": "测试会话",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "测试会话"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_conversation_default_title(self, client: AsyncClient, user_headers):
        """测试创建会话使用默认标题"""
        resp = await client.post("/api/chat/conversations", headers=user_headers, json={})
        assert resp.status_code == 201
        assert resp.json()["title"] == "新对话"

    async def test_create_conversation_no_auth(self, client: AsyncClient):
        """测试未登录创建会话返回401"""
        resp = await client.post("/api/chat/conversations", json={
            "title": "未认证会话",
        })
        assert resp.status_code == 401


class TestListConversations:
    """会话列表测试"""

    async def test_list_conversations_empty(self, client: AsyncClient, user_headers):
        """测试空会话列表"""
        resp = await client.get("/api/chat/conversations", headers=user_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_conversations_multiple(self, client: AsyncClient, user_headers):
        """测试获取多个会话"""
        # 创建两个会话
        await client.post("/api/chat/conversations", headers=user_headers, json={
            "title": "会话1",
        })
        await client.post("/api/chat/conversations", headers=user_headers, json={
            "title": "会话2",
        })
        resp = await client.get("/api/chat/conversations", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        titles = {c["title"] for c in data}
        assert titles == {"会话1", "会话2"}

    async def test_list_conversations_user_isolation(self, client: AsyncClient, admin_headers, user_headers):
        """测试用户只能看到自己的会话"""
        # 管理员创建一个会话
        await client.post("/api/chat/conversations", headers=admin_headers, json={
            "title": "管理员会话",
        })
        # 普通用户创建一个会话
        await client.post("/api/chat/conversations", headers=user_headers, json={
            "title": "用户会话",
        })
        # 普通用户只能看到自己的
        resp = await client.get("/api/chat/conversations", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "用户会话"


class TestGetConversation:
    """获取单个会话测试"""

    async def test_get_conversation_with_messages(self, client: AsyncClient, user_headers):
        """测试获取会话详情（含消息列表）"""
        # 创建会话
        create_resp = await client.post("/api/chat/conversations", headers=user_headers, json={
            "title": "详情会话",
        })
        conv_id = create_resp.json()["id"]
        # 获取详情
        resp = await client.get(f"/api/chat/conversations/{conv_id}", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conv_id
        assert data["title"] == "详情会话"
        assert "messages" in data
        assert isinstance(data["messages"], list)

    async def test_get_conversation_not_found(self, client: AsyncClient, user_headers):
        """测试获取不存在的会话返回404"""
        resp = await client.get("/api/chat/conversations/9999", headers=user_headers)
        assert resp.status_code == 404

    async def test_get_other_user_conversation(self, client: AsyncClient, admin_headers, user_headers):
        """测试无法获取其他用户的会话"""
        # 管理员创建会话
        create_resp = await client.post("/api/chat/conversations", headers=admin_headers, json={
            "title": "管理员私有会话",
        })
        conv_id = create_resp.json()["id"]
        # 普通用户尝试获取
        resp = await client.get(f"/api/chat/conversations/{conv_id}", headers=user_headers)
        assert resp.status_code == 404


class TestDeleteConversation:
    """删除会话测试"""

    async def test_delete_conversation_success(self, client: AsyncClient, user_headers):
        """测试正常删除会话"""
        # 创建会话
        create_resp = await client.post("/api/chat/conversations", headers=user_headers, json={
            "title": "待删除会话",
        })
        conv_id = create_resp.json()["id"]
        # 删除
        resp = await client.delete(f"/api/chat/conversations/{conv_id}", headers=user_headers)
        assert resp.status_code == 200
        assert "已删除" in resp.json()["message"]
        # 确认已删除
        resp = await client.get(f"/api/chat/conversations/{conv_id}", headers=user_headers)
        assert resp.status_code == 404

    async def test_delete_conversation_not_found(self, client: AsyncClient, user_headers):
        """测试删除不存在的会话返回404"""
        resp = await client.delete("/api/chat/conversations/9999", headers=user_headers)
        assert resp.status_code == 404

    async def test_delete_other_user_conversation(self, client: AsyncClient, admin_headers, user_headers):
        """测试无法删除其他用户的会话"""
        # 管理员创建会话
        create_resp = await client.post("/api/chat/conversations", headers=admin_headers, json={
            "title": "管理员会话",
        })
        conv_id = create_resp.json()["id"]
        # 普通用户尝试删除
        resp = await client.delete(f"/api/chat/conversations/{conv_id}", headers=user_headers)
        assert resp.status_code == 404
