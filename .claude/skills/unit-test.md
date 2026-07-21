---
name: unit-test
description: 项目单元测试技能。支持运行后端pytest测试、编写新测试用例、查看测试覆盖率。
skill_type: project
---

# unit-test

> RAG电商知识库问答系统 — 单元测试技能

## 功能概述

| 操作 | 说明 | 触发词 |
|------|------|--------|
| **运行所有测试** | 执行全部pytest测试用例并展示结果 | "跑测试"、"运行测试" |
| **编写新测试** | 为指定功能新增测试用例 | "写测试"、"加测试" |
| **查看覆盖率** | 生成并展示代码覆盖率报告 | "覆盖率"、"测试覆盖" |
| **更新测试** | 修改代码后同步更新已有测试 | "更新测试" |

## 项目测试架构

```
LangChainRAG项目/
├── backend/
│   ├── tests/
│   │   ├── conftest.py           ← 测试配置、fixtures
│   │   ├── test_auth.py          ← 用户认证测试
│   │   ├── test_chat.py          ← 会话管理测试
│   │   ├── test_knowledge.py     ← 知识库管理测试
│   │   └── test_rag_service.py   ← RAG服务测试
│   └── pytest.ini
└── frontend/
    └── src/__tests__/            ← 前端测试（可选）
```

- **测试框架**：pytest + pytest-asyncio
- **API测试**：httpx.AsyncClient + FastAPI TestClient
- **测试数据库**：SQLite内存模式，每次测试独立
- **Mock策略**：外部服务（Redis、DashScope API、Chroma）使用mock

## 测试覆盖的功能模块

| 模块 | 测试文件 | 测试内容 |
|------|----------|----------|
| 用户认证 | test_auth.py | 注册、登录、JWT、修改密码、角色权限 |
| 会话管理 | test_chat.py | 创建/列表/删除会话、消息加载 |
| 知识库管理 | test_knowledge.py | 文档上传、列表、删除、权限校验 |
| RAG服务 | test_rag_service.py | 文档分块、缓存命中/未命中 |

## 如何写测试？

### conftest.py 基础fixtures

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, engine, Base

@pytest.fixture(autouse=True)
async def setup_db():
    """每个测试前重建数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest.fixture
async def client():
    """异步测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def admin_token(client):
    """获取管理员token"""
    resp = await client.post("/api/auth/login", json={
        "username": "jincong", "password": "123456"
    })
    return resp.json()["access_token"]

@pytest.fixture
async def user_token(client):
    """获取普通用户token"""
    await client.post("/api/auth/register", json={
        "username": "testuser", "password": "test123"
    })
    resp = await client.post("/api/auth/login", json={
        "username": "testuser", "password": "test123"
    })
    return resp.json()["access_token"]
```

### 测试模板

```python
import pytest

class TestAuth:
    """用户认证模块测试"""

    @pytest.mark.asyncio
    async def test_register_success(self, client):
        """测试正常注册"""
        resp = await client.post("/api/auth/register", json={
            "username": "newuser", "password": "pass123"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["role"] == "user"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client):
        """测试重复用户名注册应返回400"""
        data = {"username": "dupuser", "password": "pass123"}
        await client.post("/api/auth/register", json=data)
        resp = await client.post("/api/auth/register", json=data)
        assert resp.status_code == 400
        assert "已存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        """测试密码错误应返回401"""
        await client.post("/api/auth/register", json={
            "username": "user1", "password": "pass123"
        })
        resp = await client.post("/api/auth/login", json={
            "username": "user1", "password": "wrong"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_requires_role(self, client, user_token):
        """测试普通用户无法访问管理员接口"""
        resp = await client.get("/api/knowledge/documents",
            headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 403
```

### 常用断言

```python
assert resp.status_code == 200           # 状态码
assert "key" in resp.json()              # JSON包含字段
assert resp.json()["field"] == value     # 字段值相等
assert len(resp.json()) == 3             # 列表长度
assert "错误信息" in resp.json()["detail"]  # 错误消息包含
```

## 命令参考

```bash
# 运行所有测试
cd backend && ../.venv/Scripts/python -m pytest tests/ -v

# 运行指定测试文件
../.venv/Scripts/python -m pytest tests/test_auth.py -v

# 运行指定测试类/方法
../.venv/Scripts/python -m pytest tests/test_auth.py::TestAuth::test_register_success -v

# 生成覆盖率报告
../.venv/Scripts/python -m pytest tests/ --cov=app --cov-report=term-missing

# 生成HTML覆盖率报告
../.venv/Scripts/python -m pytest tests/ --cov=app --cov-report=html
```

## 工作约定

1. 在编写新测试之前，先阅读已有测试了解风格和结构
2. 测试应独立运行，不依赖外部服务（使用mock）
3. 每个测试只测一个功能点
4. 测试运行后，如实汇报结果
5. 如果测试失败，给出具体的修复建议
