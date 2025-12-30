FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run sets PORT environment variable
ENV HOST=0.0.0.0
ENV MCP_TRANSPORT=sse

EXPOSE 8080

# Run simple server (no OAuth, no migrations needed)
CMD ["python", "server_simple.py"]
