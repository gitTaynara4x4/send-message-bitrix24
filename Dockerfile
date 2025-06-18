FROM python:3.11-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

# Define fuso padrão (opcional, apenas para o sistema)
ENV TZ=America/Sao_Paulo

# Cria diretório de trabalho
WORKDIR /app

# Copia arquivos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expõe porta do Flask
EXPOSE 1444

# Roda a aplicação
CMD ["python", "main.py"]
