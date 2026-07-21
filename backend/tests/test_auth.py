"""用户认证模块测试：注册、登录、JWT、修改密码"""
import pytest
from httpx import AsyncClient


class TestRegister:
    """用户注册测试"""

    async def test_register_success(self, client: AsyncClient):
        """测试正常注册"""
        resp = await client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "pass123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data

    async def test_register_duplicate_username(self, client: AsyncClient):
        """测试重复用户名注册返回400"""
        data = {"username": "dupuser", "password": "pass123"}
        # 第一次注册成功
        resp1 = await client.post("/api/auth/register", json=data)
        assert resp1.status_code == 201
        # 第二次注册失败
        resp2 = await client.post("/api/auth/register", json=data)
        assert resp2.status_code == 400
        assert "已存在" in resp2.json()["detail"]

    async def test_register_duplicate_admin_username(self, client: AsyncClient):
        """测试注册与管理员同名的用户返回400"""
        resp = await client.post("/api/auth/register", json={
            "username": "jincong",
            "password": "pass123",
        })
        assert resp.status_code == 400

    async def test_register_short_password(self, client: AsyncClient):
        """测试密码过短注册失败"""
        resp = await client.post("/api/auth/register", json={
            "username": "shortpwd",
            "password": "12345",  # min_length=6
        })
        assert resp.status_code == 422


class TestLogin:
    """用户登录测试"""

    async def test_login_success(self, client: AsyncClient):
        """测试正常登录，返回access_token和refresh_token"""
        # 先注册
        await client.post("/api/auth/register", json={
            "username": "loginuser",
            "password": "pass123",
        })
        # 登录
        resp = await client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "pass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        """测试密码错误返回401"""
        await client.post("/api/auth/register", json={
            "username": "user1",
            "password": "pass123",
        })
        resp = await client.post("/api/auth/login", json={
            "username": "user1",
            "password": "wrongpass",
        })
        assert resp.status_code == 401
        assert "错误" in resp.json()["detail"]

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试不存在的用户登录返回401"""
        resp = await client.post("/api/auth/login", json={
            "username": "nobody",
            "password": "pass123",
        })
        assert resp.status_code == 401

    async def test_login_admin_user(self, client: AsyncClient):
        """测试管理员账号登录"""
        resp = await client.post("/api/auth/login", json={
            "username": "jincong",
            "password": "123456",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()


class TestCurrentUser:
    """获取当前用户信息测试"""

    async def test_get_me_admin(self, client: AsyncClient, admin_headers):
        """测试管理员获取当前用户信息"""
        resp = await client.get("/api/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "jincong"
        assert data["role"] == "admin"
        assert "id" in data

    async def test_get_me_user(self, client: AsyncClient, user_headers):
        """测试普通用户获取当前用户信息"""
        resp = await client.get("/api/auth/me", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["role"] == "user"

    async def test_get_me_no_token(self, client: AsyncClient):
        """测试未登录访问返回401"""
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        """测试无效token返回401"""
        resp = await client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid_token_here",
        })
        assert resp.status_code == 401


class TestChangePassword:
    """修改密码测试"""

    async def test_change_password_success(self, client: AsyncClient):
        """测试正常修改密码"""
        # 注册
        await client.post("/api/auth/register", json={
            "username": "pwduser",
            "password": "oldpass",
        })
        # 登录获取token
        login_resp = await client.post("/api/auth/login", json={
            "username": "pwduser",
            "password": "oldpass",
        })
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        # 修改密码
        resp = await client.put("/api/auth/password", headers=headers, json={
            "old_password": "oldpass",
            "new_password": "newpass123",
        })
        assert resp.status_code == 200
        assert "成功" in resp.json()["message"]
        # 用新密码登录验证
        resp = await client.post("/api/auth/login", json={
            "username": "pwduser",
            "password": "newpass123",
        })
        assert resp.status_code == 200

    async def test_change_password_wrong_old(self, client: AsyncClient):
        """测试旧密码错误返回400"""
        await client.post("/api/auth/register", json={
            "username": "pwduser2",
            "password": "oldpass",
        })
        login_resp = await client.post("/api/auth/login", json={
            "username": "pwduser2",
            "password": "oldpass",
        })
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        resp = await client.put("/api/auth/password", headers=headers, json={
            "old_password": "wrongold",
            "new_password": "newpass123",
        })
        assert resp.status_code == 400
        assert "旧密码" in resp.json()["detail"]
