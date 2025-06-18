FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    build-essential \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Sao_Paulo

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 1444

# Roda a aplicação
CMD ["python", "main.py"]
