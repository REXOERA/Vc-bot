FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN git clone --depth 1 --branch 1.3.1 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    /opt/bgutil

RUN cd /opt/bgutil/server && npm install && npx tsc

COPY bot.py .

CMD ["sh", "-c", "node /opt/bgutil/server/build/main.js & python bot.py"]
