# Backend image for the t3.small EC2 instance (FastAPI, Chroma, embeddings).
#
# Torch is the CPU wheel. The default PyPI wheel is the CUDA build, which is
# about 2 GB and cannot load on a 1–2 GiB instance. CPU torch is installed
# first, and the build fails if a CUDA build replaced it.
#
# One process only. A second uvicorn worker would load all-MiniLM-L6-v2 again
# and the instance would run out of memory.

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    HF_HOME=/cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/cache/huggingface \
    TRANSFORMERS_CACHE=/cache/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    CUDA_VISIBLE_DEVICES="" \
    CODELENS_KB=/data/chroma \
    CODELENS_LOW_MEMORY=1 \
    WEB_CONCURRENCY=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-prod.txt .
RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements-prod.txt \
    && python -c "import torch; assert torch.version.cuda is None, 'CUDA torch wheel slipped in: ' + torch.__version__"

COPY knowledge_base ./knowledge_base
COPY rag_core ./rag_core
COPY deploy/docker/entrypoint.sh /entrypoint.sh

RUN groupadd --gid 10001 codelens \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin codelens \
    && mkdir -p /data/chroma /cache/huggingface \
    && chown -R codelens:codelens /app /data /cache \
    && chmod 755 /entrypoint.sh

USER codelens

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=8).read()"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "rag_core.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "75"]
