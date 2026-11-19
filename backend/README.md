---
title: RAG 电商知识库问答 API
emoji: 🛍️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# RAG 电商知识库问答 · 后端服务

基于 FastAPI + LangChain + 通义千问的 RAG 知识库问答后端，面向电商客服场景。

## 接口

- `GET /health` 健康检查
- `GET /docs` Swagger 文档
- `POST /api/auth/register` 注册
- `POST /api/auth/login` 登录
- `POST /api/chat/stream` SSE 流式问答
- `POST /api/knowledge/upload` 上传文档（管理员）

## 环境变量（在 Space Settings → Variables and secrets 中配置）

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | 通义千问 API Key（secret） |
| `QWEN_MODEL` | 模型名，默认 `qwen3.8-flash` |
| `QWEN_API_BASE` | OpenAI 兼容接口地址 |
| `JWT_SECRET_KEY` | JWT 签名密钥（secret） |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 管理员账号（公开演示建议修改密码） |
| `SEED_DEMO_DATA` | 设为 `true` 时，知识库为空会自动导入 `demo_data/` 示例文档 |
| `PROXY_SECRET` | 与 Cloudflare Pages 的 `PROXY_SECRET` 一致，用于识别真实用户 IP |
| `RATE_LIMIT_PER_MINUTE` | 每 IP 每分钟请求上限，默认 30 |

## 注意

- 免费版 Space 的磁盘不持久：容器重启后会重新初始化数据库，并重新导入示例文档；会话历史不会保留。
- 首次启动会在后台加载 embedding 模型（构建时已预下载），约 10–30 秒。
