FROM python:3.11-slim

RUN apt-get update && apt-get install -y ttyd && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

EXPOSE 7681

CMD ["ttyd", "-p", "7681", "python3", "devbuild_tetris.py"]