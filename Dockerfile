# bullseye is archived (apt 404 on Render) -> use bookworm
FROM python:3.10-slim-bookworm

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    COOKIES_FILE_PATH="youtube_cookies.txt"

# System deps: ffmpeg, aria2 (downloads), build tools for Bento4 mp4decrypt + tgcrypto
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential gcc libffi-dev ffmpeg aria2 wget unzip cmake git ca-certificates \
    && wget -q https://github.com/axiomatic-systems/Bento4/archive/v1.6.0-639.zip \
    && unzip -q v1.6.0-639.zip \
    && cd Bento4-1.6.0-639 && mkdir build && cd build \
    && cmake .. && make -j"$(nproc)" mp4decrypt \
    && cp mp4decrypt /usr/local/bin/ \
    && cd /app && rm -rf Bento4-1.6.0-639 v1.6.0-639.zip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -U yt-dlp

COPY . .

# Flask keep-alive (Render PORT) + the Telegram bot
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000} & exec python3 -m Extractor"]
