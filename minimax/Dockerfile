FROM ghcr.io/ace-step/ace-step-1.5:latest

WORKDIR /opt/comfy
RUN git init . \
    && git fetch --depth 1 https://github.com/Comfy-Org/ComfyUI.git 7c78b5641ab2d6cb7f7766a183a8a43a59de0a8b \
    && git checkout --detach FETCH_HEAD \
    && uv pip install --python /app/.venv/bin/python -r requirements.txt

# Use the Blackwell acceleration path in ComfyUI's quantized kernels.
RUN uv pip install --python /app/.venv/bin/python \
    --index https://download.pytorch.org/whl/cu130 \
    torch==2.10.0+cu130 torchvision==0.25.0+cu130 torchaudio==2.10.0+cu130

# cuDNN opens NVRTC at runtime to compile attention kernels.
ENV TORCH_CUDA_LIB=/app/.venv/lib/python3.11/site-packages/nvidia/cu13/lib
RUN ln -sf libnvrtc.so.13 "$TORCH_CUDA_LIB/libnvrtc.so"
ENV LD_LIBRARY_PATH=$TORCH_CUDA_LIB:$LD_LIBRARY_PATH

ENTRYPOINT ["/app/.venv/bin/python", "main.py"]
CMD ["--listen", "0.0.0.0", "--port", "8188", "--output-directory", "/output", "--lowvram", "--reserve-vram", "1", "--disable-smart-memory", "--cache-none", "--disable-metadata", "--disable-all-custom-nodes", "--disable-api-nodes", "--disable-auto-launch"]
