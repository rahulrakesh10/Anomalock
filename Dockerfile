FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY src/ src/
COPY api/ api/
COPY artifacts/ artifacts/
COPY data/external/cities15000.txt data/external/cities15000.txt

ENV PYTHONPATH=/app/src

EXPOSE 8080
CMD ["python", "-m", "uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
