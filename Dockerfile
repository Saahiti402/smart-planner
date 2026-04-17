# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS python-base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1


FROM python-base AS backend-deps

COPY requirements.backend.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip \
    && python -m pip install -r requirements.backend.txt


FROM python-base AS backend

ENV HF_HOME=/app/.cache/huggingface

COPY --from=backend-deps /usr/local /usr/local
COPY app ./app
COPY rag_docs ./rag_docs

EXPOSE 8000


FROM python-base AS frontend-deps

COPY requirements.frontend.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip \
    && python -m pip install -r requirements.frontend.txt


FROM python-base AS frontend

COPY --from=frontend-deps /usr/local /usr/local
COPY streamlit_app.py .

EXPOSE 8501
