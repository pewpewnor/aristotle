FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN pip install uv
RUN python3.13 -m uv sync

EXPOSE 8000

CMD ["python3.13", "-m", "uv", "run", "uvicorn", "src.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
