FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY patent_service/requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt \
    && python3 -m uvicorn --version

COPY patent_service/ /app/patent_service/
ENV PYTHONPATH=/app

EXPOSE 8000

ENTRYPOINT ["python3", "-m", "uvicorn", "patent_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
