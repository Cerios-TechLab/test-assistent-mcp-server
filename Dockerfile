FROM python:3.11-slim

WORKDIR /app

COPY server/ server/
COPY pyproject.toml .

RUN pip install --no-cache-dir "mcp>=1.29.0,<2"

ENV PYTHONPATH=/app

# Run-time python differs per environment: after `uv sync` (Glama's build spec)
# packages live in /app/.venv; after plain docker build they live in the system
# python site-packages. Prefer the venv when present.
CMD ["sh", "-c", "if [ -x .venv/bin/python ]; then exec .venv/bin/python -m server.testassist_mcp_server; else exec python -m server.testassist_mcp_server; fi"]
