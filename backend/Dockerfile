FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# torch / onnxruntime 依赖的 OpenMP 运行时
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# 先装 CPU 版 torch，避免 pip 拉取数 GB 的 CUDA 依赖，显著缩短构建时间与镜像体积
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY demo_data ./demo_data

# 构建时预下载 embedding 模型，避免容器冷启动时再从网络下载
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-small-zh-v1.5', local_dir='/app/models/bge-small-zh-v1.5')"

# Hugging Face Spaces 容器以非 root 用户运行，确保应用目录可写（SQLite/Chroma/uploads）
RUN useradd -m -u 1000 user \
    && chown -R user:user /app
USER user

ENV HOME=/home/user

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
