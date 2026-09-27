FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# CPU-only torch wheels (no CUDA needed for the demo)
RUN pip install --no-cache-dir torch==2.4.1 torchvision==0.19.2 \
      --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
