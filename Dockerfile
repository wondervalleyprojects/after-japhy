FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The application. The index (128MB: BM25 pickle, chunk lookup, SQLite FTS5)
# is baked into the image from the local directory at deploy time — it is
# never committed to git.
COPY app.py model_seam.py system_prompt.txt ./
COPY static/ static/
COPY index/ index/

# Session logs land on the mounted volume, not the ephemeral container disk
ENV LOGS_DIR=/data/logs

EXPOSE 8080

# One worker: the BM25 index holds ~450MB RAM per process. Threads are cheap.
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "120"]
