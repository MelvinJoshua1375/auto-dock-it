FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y pandoc

COPY . .

EXPOSE 8000

USER app

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myapp.server:app"]

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1