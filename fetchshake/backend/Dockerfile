
FROM python:3.12-slim

WORKDIR /app

# Install FFmpeg and tools required to install Deno
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno for yt-dlp JavaScript challenge solving
ENV DENO_INSTALL=/usr/local
ENV PATH="/usr/local/bin:${PATH}"

RUN curl -fsSL https://deno.land/install.sh | sh

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app ./app

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
