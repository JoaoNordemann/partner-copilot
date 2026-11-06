# CPU-only image. Embedding weights are downloaded at runtime, never during build.
FROM python:3.13-slim AS cpu
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    LLM_BACKEND=fake EMBEDDING_DEVICE=cpu CHROMA_PATH=/state/chroma \
    HF_HOME=/state/hf API_EMBEDDING_CACHE=/state/hf/sentence-transformers \
    API_ALLOW_MODEL_DOWNLOAD=true API_REPLAY_CATALOG=/recordings/catalog.json \
    API_HOST=0.0.0.0 API_PORT=8000 HOME=/home/copilot
WORKDIR /app
COPY requirements-cpu.txt ./
RUN python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2,<3" \
    && python -m pip install -r requirements-cpu.txt
COPY pyproject.toml README.md ./
COPY src/ src/
COPY data/splits/ data/splits/
COPY data/raw/restaurants.json data/raw/restaurants.json
COPY configs/ configs/
RUN python -m pip install --no-deps . \
    && useradd --uid 10001 --create-home copilot \
    && mkdir -p /state /recordings && chown -R copilot:copilot /state /recordings
USER 10001:10001
EXPOSE 8000
VOLUME ["/state"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=3 \
    CMD ["python", "-m", "partner_copilot.container", "healthcheck"]
ENTRYPOINT ["python", "-m", "partner_copilot.container"]
