FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.lock ./
# CPU-only torch wheels first (no CUDA needed for the demo), then the rest.
# The lockfile wins when present (exact resolved versions); requirements.txt
# is the range-based fallback so the build never depends on lock freshness.
RUN pip install --no-cache-dir torch==2.4.1 \
      --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir $( [ -s requirements.lock ] \
        && echo "--no-deps -r requirements.lock" || echo "-r requirements.txt" )

COPY app ./app
COPY scripts ./scripts
COPY pytest.ini ./
COPY data ./data

# data/processed is generated at startup (or mounted as a volume); raw/ stays
# a placeholder for optional user-supplied real data.
RUN mkdir -p data/processed data/raw \
    && useradd --create-home --uid 10001 vayu \
    && chown -R vayu:vayu /app
USER vayu

EXPOSE 8000

# Healthcheck hits the plain /health route (section 11.3).
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
