# Stage 1: build de dependências
FROM public.ecr.aws/docker/library/python:3.12-slim
 AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: imagem final
FROM public.ecr.aws/docker/library/python:3.12-slim


ENV PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

WORKDIR /app

# Copia dependências do builder
COPY --from=builder /root/.local /root/.local

# Copia código da aplicação
COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
