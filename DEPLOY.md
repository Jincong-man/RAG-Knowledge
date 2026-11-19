# 部署到线上（Cloudflare Pages + Hugging Face Spaces，全部免费）

目标：得到一个可以写进简历的稳定在线地址，例如 `https://rag-knowledge.pages.dev`。

```
浏览器
  │  https://<项目名>.pages.dev        ← Cloudflare Pages（Vue 静态站点，免费）
  │      └─ /api/* 由 Pages Function 反向代理（同源，无跨域）
  ▼
https://<用户名>-<空间名>.hf.space     ← Hugging Face Space（FastAPI + Chroma，Docker，免费）
```

> 你之前在 Cloudflare 点的是「Worker 直连 Git 仓库」，那条路径会把整个 Python 仓库当成 JS Worker 构建，无法运行本项目，请改用下面的 **Pages** 流程。

---

## 0. 前置条件

- GitHub 仓库：`Jincong-man/RAG-Knowledge`（本地改动需要先 push）
- [Hugging Face](https://huggingface.co) 账号（免费）
- [Cloudflare](https://dash.cloudflare.com) 账号（免费）
- 通义千问 `DASHSCOPE_API_KEY`（已在本机 `backend/.env` 中）

---

## 1. 部署后端到 Hugging Face Spaces

### 1.1 创建 Space

1. 打开 <https://huggingface.co/new-space>
2. **Space name** 填 `rag-knowledge`
3. **License** 随意（如 MIT）
4. **Select the Space SDK** 选 **Docker** → **Blank**
5. **Hardware** 选 **CPU basic（free）**
6. **Visibility** 选 **Public**
7. 点击 **Create Space**

创建后的地址形如：`https://<你的HF用户名>-rag-knowledge.hf.space`

### 1.2 配置环境变量（Settings → Variables and secrets）

| 类型 | 名称 | 值 |
|------|------|----|
| Secret | `DASHSCOPE_API_KEY` | 你 `backend/.env` 里的值 |
| Secret | `JWT_SECRET_KEY` | 随机长字符串，例如 `openssl rand -hex 32` |
| Secret | `PROXY_SECRET` | 随机字符串，需与 Cloudflare Pages 中同名变量一致 |
| Variable | `QWEN_MODEL` | `qwen3.8-flash` |
| Variable | `QWEN_API_BASE` | `https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1` |
| Variable | `QWEN_ENABLE_THINKING` | `false`（关闭思考模式，首字更快；需要深度推理时改为 `true`） |
| Variable | `SEED_DEMO_DATA` | `true`（知识库为空时自动导入示例文档） |
| Variable | `ADMIN_USERNAME` | `jincong` |
| Secret | `ADMIN_PASSWORD` | 自定义的管理员密码（不要用默认 123456） |
| Variable | `RATE_LIMIT_PER_MINUTE` | `20` |

> 免费 Space 会在闲置约 48 小时后休眠，下一次访问自动唤醒（约 10–30 秒）；磁盘不持久，重启后数据库与上传文件会重置，示例文档会自动重新导入。

### 1.3 推送后端代码

本仓库的 `backend/` 目录已经包含 `Dockerfile` 和供 Space 识别的 `README.md`，只需要把 **backend 目录的内容**推到 Space 仓库根目录。

**方式 A：使用 huggingface CLI（推荐）**

```bash
pip install -U "huggingface_hub[cli]"
hf auth login            # 粘贴有 write 权限的 Access Token

cd "d:/Vibe-Coding/LangChainRAG项目"
hf upload <HF用户名>/rag-knowledge ./backend . --repo-type=space \
  --exclude ".env" ".venv/**" "__pycache__/**" "**/__pycache__/**" \
            "app.db*" "chroma_data/**" "uploads/**" "models/**" \
            "tests/**" "pytest.ini"
```

Space 会自动开始构建，首次构建约 10–20 分钟（需要安装 PyTorch CPU 版并预下载 embedding 模型）。在 Space 页面 **Logs → Build** 可以看到进度。

**方式 B：git subtree**

```bash
cd "d:/Vibe-Coding/LangChainRAG项目"
git subtree split --prefix backend -b hf-deploy
git remote add hf https://huggingface.co/spaces/<HF用户名>/rag-knowledge
git push hf hf-deploy:main --force
```

后续更新：重新执行 `git branch -D hf-deploy && git subtree split --prefix backend -b hf-deploy && git push hf hf-deploy:main --force`。

### 1.4 验证后端

浏览器打开：

- `https://<HF用户名>-rag-knowledge.hf.space/health` → 应返回 `{"status":"ok"}`
- `https://<HF用户名>-rag-knowledge.hf.space/docs` → Swagger 文档

首次启动后，Space 日志中应出现「演示文档导入完成」。可以在 Swagger 里用管理员账号登录，`GET /api/knowledge/documents` 应能看到 4 个示例文档。

---

## 2. 部署前端到 Cloudflare Pages

### 2.1 连接 Git 仓库

1. 进入 <https://dash.cloudflare.com> → **Workers & Pages** → **Create**
2. 切到 **Pages** 标签页 → **Connect to Git**（不要选 Worker）
3. 授权并选择仓库 `Jincong-man/RAG-Knowledge`
4. 项目名填 `rag-knowledge`（决定了 `rag-knowledge.pages.dev` 地址）

### 2.2 构建配置

| 配置项 | 值 |
|--------|----|
| Framework preset | `Vite` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| **Root directory（Advanced）** | `frontend` |

### 2.3 环境变量（Environment variables）

| 名称 | 值 |
|------|----|
| `BACKEND_URL` | `https://<HF用户名>-rag-knowledge.hf.space` |
| `PROXY_SECRET` | 与 HF Space 中同名 Secret 完全一致 |
| `NODE_VERSION` | `20` |

点击 **Save and Deploy**。构建完成后访问 `https://rag-knowledge.pages.dev`。

`frontend/functions/api/[[path]].js` 会把 `/api/*` 转发到 `BACKEND_URL`，因此前后端同源，不依赖 CORS，SSE 流式回答也能正常透传。

### 2.4 验证

1. 打开 Pages 地址 → 注册一个账号并登录
2. 进入「问答」→ 提问「AirBook 14 的屏幕参数是什么？」→ 应流式回答并显示引用来源
3. 管理员登录后进入「知识库管理」→ 应看到 4 个已就绪的示例文档

---

## 3. 可选：绑定自己的域名

Pages 项目 → **Custom domains** → 添加域名并按提示配置 CNAME。Cloudflare 免费套餐即可，无需备案（域名注册商要求除外）。

---

## 4. 常见问题

| 现象 | 原因 / 处理 |
|------|-------------|
| Pages 打开正常，提问报 500「后端未配置」 | Pages 环境变量缺少 `BACKEND_URL`，修改后需重新部署 |
| 提问报 502 / 长时间无响应 | HF Space 正在冷启动或构建中，先去 Space 页面查看状态；唤醒后重试 |
| 首次提问特别慢 | 免费 CPU 实例性能有限，embedding 模型首次加载需 10–30 秒 |
| Space 重启后历史对话消失、需要重新注册 | 免费版磁盘不持久，属于预期行为；示例文档会自动重新导入 |
| 通义千问返回 401/403 | `DASHSCOPE_API_KEY` 或 `QWEN_API_BASE` 配置错误 |
| 提示「模型API额度已用尽」 | 该账号/工作空间的免费额度耗尽：到百炼控制台充值或关闭「仅用免费额度」，或在 HF Space 把 `QWEN_MODEL` 换成仍有额度的模型（如 `glm-5.3-prime`、`deepseek-v4.1-flash`） |
| 页面刷新 404 | 确认 `frontend/public/_redirects` 已随构建产物发布到 `dist` |
| 提示「请求过于频繁」 | 触发了 `RATE_LIMIT_PER_MINUTE`，可调大或等待一分钟 |

---

## 5. 成本

| 项目 | 费用 |
|------|------|
| Cloudflare Pages | 免费（每月 500 次构建、无限静态请求） |
| Cloudflare Pages Functions | 免费（每天 10 万次请求） |
| Hugging Face Space（CPU basic） | 免费（闲置休眠、磁盘不持久） |
| 通义千问 API | 按量计费，已配置每分钟限流 |

如果后续希望数据持久化、网站不休眠，可把后端迁移到 Railway / 轻量云服务器，前端 Pages 配置与 `BACKEND_URL` 保持不变即可。
