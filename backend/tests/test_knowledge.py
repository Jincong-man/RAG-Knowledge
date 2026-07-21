"""知识库管理模块测试：上传、列表、删除、权限控制"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


class TestUploadDocument:
    """文档上传测试"""

    async def test_admin_upload_document(self, client: AsyncClient, admin_headers):
        """测试管理员上传文档成功"""
        with patch("app.services.doc_service.process_document", new_callable=AsyncMock):
            resp = await client.post(
                "/api/knowledge/upload",
                headers=admin_headers,
                files={"file": ("test.txt", b"Test document content", "text/plain")},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "test.txt"
        assert data["file_type"] == ".txt"
        assert data["file_size"] == len(b"Test document content")
        assert "id" in data

    async def test_admin_upload_unsupported_type(self, client: AsyncClient, admin_headers):
        """测试上传不支持的文件类型返回400"""
        resp = await client.post(
            "/api/knowledge/upload",
            headers=admin_headers,
            files={"file": ("test.exe", b"binary content", "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "不支持" in resp.json()["detail"]

    async def test_user_cannot_upload(self, client: AsyncClient, user_headers):
        """测试普通用户无法上传文档（403）"""
        resp = await client.post(
            "/api/knowledge/upload",
            headers=user_headers,
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        assert resp.status_code == 403

    async def test_upload_no_auth(self, client: AsyncClient):
        """测试未登录上传文档返回401"""
        resp = await client.post(
            "/api/knowledge/upload",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        assert resp.status_code == 401


class TestListDocuments:
    """文档列表测试"""

    async def test_list_documents_empty(self, client: AsyncClient, admin_headers):
        """测试空文档列表"""
        resp = await client.get("/api/knowledge/documents", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_documents_after_upload(self, client: AsyncClient, admin_headers):
        """测试上传后获取文档列表"""
        with patch("app.services.doc_service.process_document", new_callable=AsyncMock):
            await client.post(
                "/api/knowledge/upload",
                headers=admin_headers,
                files={"file": ("doc1.txt", b"Content 1", "text/plain")},
            )
            await client.post(
                "/api/knowledge/upload",
                headers=admin_headers,
                files={"file": ("doc2.txt", b"Content 2", "text/plain")},
            )
        resp = await client.get("/api/knowledge/documents", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        filenames = {d["filename"] for d in data}
        assert filenames == {"doc1.txt", "doc2.txt"}

    async def test_list_documents_user_forbidden(self, client: AsyncClient, user_headers):
        """测试普通用户无法访问文档列表"""
        resp = await client.get("/api/knowledge/documents", headers=user_headers)
        assert resp.status_code == 403


class TestDeleteDocument:
    """文档删除测试"""

    async def test_delete_document_success(self, client: AsyncClient, admin_headers):
        """测试管理员删除文档成功"""
        # 先上传
        with patch("app.services.doc_service.process_document", new_callable=AsyncMock):
            upload_resp = await client.post(
                "/api/knowledge/upload",
                headers=admin_headers,
                files={"file": ("to_delete.txt", b"Delete me", "text/plain")},
            )
        doc_id = upload_resp.json()["id"]
        # 删除
        resp = await client.delete(f"/api/knowledge/documents/{doc_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert "已删除" in resp.json()["message"]
        # 确认列表为空
        list_resp = await client.get("/api/knowledge/documents", headers=admin_headers)
        assert len(list_resp.json()) == 0

    async def test_delete_document_not_found(self, client: AsyncClient, admin_headers):
        """测试删除不存在的文档返回404"""
        resp = await client.delete("/api/knowledge/documents/9999", headers=admin_headers)
        assert resp.status_code == 404

    async def test_delete_document_user_forbidden(self, client: AsyncClient, admin_headers, user_headers):
        """测试普通用户无法删除文档"""
        # 管理员上传
        with patch("app.services.doc_service.process_document", new_callable=AsyncMock):
            upload_resp = await client.post(
                "/api/knowledge/upload",
                headers=admin_headers,
                files={"file": ("protected.txt", b"Protected", "text/plain")},
            )
        doc_id = upload_resp.json()["id"]
        # 普通用户尝试删除
        resp = await client.delete(f"/api/knowledge/documents/{doc_id}", headers=user_headers)
        assert resp.status_code == 403
