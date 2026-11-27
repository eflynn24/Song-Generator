FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 HF_HOME=/root/.cache/huggingface
WORKDIR /opt/yue2

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu128 torch==2.10.0 \
    && git clone --depth 1 https://github.com/multimodal-art-projection/YuE.git . \
    && python -m pip install --no-cache-dir .

COPY worker.py /opt/yue2/worker.py
EXPOSE 8189
CMD ["python", "worker.py"]
