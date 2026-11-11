FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=8

WORKDIR /app

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

RUN useradd --create-home appuser && chown appuser /app


FROM base AS api

COPY --chown=appuser backend/app ./app

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM base AS agents

ENV HF_HOME=/app/.cache/huggingface \
    ANONYMIZED_TELEMETRY=False

COPY backend/requirements-agents.txt /tmp/agent-requirements.txt
COPY member3_rag/requirements.txt /tmp/rag-requirements.txt

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN --mount=type=cache,target=/root/.cache/pip pip install -r /tmp/agent-requirements.txt -r /tmp/rag-requirements.txt

COPY --chown=appuser member3_rag ./member3_rag

USER appuser

RUN python -m member3_rag.rag_interface --build
RUN python -c "from member3_rag.rag_interface import get_collection; n = get_collection().count(); assert n > 0, 'Index is empty'; print(n, 'passages indexed')"

COPY --chown=appuser backend/app ./app

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

CMD ["python", "-m", "app.worker"]
