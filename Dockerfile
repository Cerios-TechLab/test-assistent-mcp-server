FROM python:3.11-slim

WORKDIR /app

COPY server/ server/
COPY knowledge/ knowledge/
COPY pyproject.toml .

RUN pip install --no-cache-dir "mcp>=1.29.0,<2"

ENV PYTHONPATH=/app
ENV TESTASSIST_KNOWLEDGE_DIR=/app/knowledge

CMD ["python", "-m", "server.testassist_mcp_server"]