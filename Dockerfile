FROM python:3.10.11-slim

WORKDIR /app

# System dependencies: ffmpeg, aria2 (downloads), Bento4 mp4decrypt (DRM videos)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc libffi-dev ffmpeg aria2 wget unzip cmake git \
    && wget -q https://github.com/axiomatic-systems/Bento4/archive/v1.6.0-639.zip \
    && unzip -q v1.6.0-639.zip \
    && cd Bento4-1.6.0-639 && mkdir build && cd build \
    && cmake .. && make -j"$(nproc)" \
    && cp mp4decrypt /usr/local/bin/ \
    && cd /app && rm -rf Bento4-1.6.0-639 v1.6.0-639.zip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -U yt-dlp

# App code
COPY . .

ENV COOKIES_FILE_PATH="youtube_cookies.txt"

# Flask keep-alive (Render/Heroku PORT) + the Telegram bot
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000} & exec python3 -m Extractor"]
