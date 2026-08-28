# sc2wav — hosted SoundCloud→WAV web app.
# Bakes in ffmpeg so no local setup is ever needed; runs under gunicorn.
FROM python:3.12-slim

# ffmpeg is required to produce WAV files.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hosting platforms inject $PORT; default to 8000 for plain `docker run`.
ENV PORT=8000
EXPOSE 8000

# gunicorn with a long timeout because downloads/conversion take time.
# Threads let a couple of downloads run concurrently.
CMD gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 --timeout 600 webapp:app
