FROM python:3-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app/

# install common packages
RUN apt-get update && apt-get upgrade -y && apt-get install --no-install-recommends -y \
    build-essential \
    python3-dev \
    git

COPY . /app/

RUN uv venv && \
    export PATH="/app/.venv/bin:$PATH" && \
    uv sync --frozen

FROM python:3-slim

WORKDIR /app/

RUN groupadd user && useradd --home-dir /app -g user user && chown -R user:user /app
RUN install -d -o user -g user /app/data

COPY --from=builder --chown=user:user /app/.venv /app/.venv
COPY --chown=user:user . /app/

USER user

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV GRANIAN_THREADS=2
ENV GRANIAN_WORKERS=2
ENV GRANIAN_BLOCKING_THREADS=4
ENV GRANIAN_INTERFACE=wsgi
ENV GRANIAN_HOST=0.0.0.0

EXPOSE 8000

CMD ["granian", "app"]
