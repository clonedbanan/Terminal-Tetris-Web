FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget ca-certificates && rm -rf /var/lib/apt/lists/*

RUN wget -O /usr/local/bin/ttyd https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 && \
    chmod +x /usr/local/bin/ttyd

WORKDIR /app

COPY . .

EXPOSE 10000

CMD ["ttyd", "-p", "10000", "-W", "python3", "web_tetris.py"]