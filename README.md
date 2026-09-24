# RAG电商知识库问答系统

基于 **LangChain + 通义千问(Qwen)** 的企业级RAG知识库问答系统，面向电商场景，支持用户通过浏览器进行知识库管理和商品智能问答。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 大模型 | 通义千问 Qwen (DashScope API) |
| Embedding | BAAI/bge-m3 |
| 向量数据库 | Chroma |
| 关系数据库 | SQLite (SQLAlchemy 2.0) |
| 缓存 | Redis |
| 认证 | JWT |
| 前端框架 | Vue.js 3 + Vite |
| UI组件库 | Element Plus |
| RAG框架 | LangChain |

## 核心功能

1. **知识库管理** - 管理员可上传/删除 PDF、Word、Excel 等文档，自动解析分块并生成向量索引
2. **RAG智能问答** - 基于知识库的上下文感知问答，流式输出，支持引用溯源
3. **多用户多会话** - 每个用户独立会话空间，支持多会话切换和管理
4. **历史持久化** - 对话记录持久化存储，跨时段登录可找回历史对话
5. **用户权限** - JWT认证，管理员/普通用户角色隔离
6. **性能优化** - 语义缓存、LLM结果缓存、频率限制、异步全链路

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Redis (可选，用于缓存)

### 1. 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
# 编辑 .env 文件，填入你的 DASHSCOPE_API_KEY

# 启动服务
uvicorn app.main:app --reload --port 8002
```

首次启动会自动：
- 创建数据库表
- 创建管理员账号 (jincong / 123456)

### 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173

前端开发服务器会把 `/api` 请求代理到后端 http://localhost:8002（见 `frontend/vite.config.js`）。

### 3. Redis (可选)

```bash
# Windows: 使用WSL或Docker运行Redis
# macOS: brew install redis && redis-server
# Linux: sudo systemctl start redis
```

如未安装Redis，系统会自动降级，仅语义缓存功能不可用。

## 使用说明

1. 访问 http://localhost:5173 进入登录页面
2. 管理员登录：`jincong` / `123456`
3. 管理员可在「知识库管理」页面上传商品相关文档
4. 普通用户注册后即可在「问答」页面提问

## 项目结构

```
LangChainRAG项目/
├── backend/                 # Python后端
│   ├── app/
│   │   ├── main.py         # FastAPI入口
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库引擎
│   │   ├── models/         # ORM模型
│   │   ├── schemas/        # Pydantic模型
│   │   ├── routers/        # API路由
│   │   ├── services/       # 业务逻辑
│   │   ├── core/           # 安全/中间件
│   │   └── rag/            # LangChain RAG组件
│   ├── requirements.txt
│   └── .env
├── frontend/                # Vue.js 3前端
│   ├── src/
│   │   ├── api/            # API请求封装
│   │   ├── views/          # 页面组件
│   │   ├── components/     # 通用组件
│   │   ├── router/         # 路由配置
│   │   └── stores/         # Pinia状态管理
│   └── package.json
└── README.md
```

## 管理员账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| jincong | 123456 | 管理员 |
