FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -g app app
RUN mkdir /app && chown app:app /app

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

USER app

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]

HEALTHCHECK CMD curl -f http://localhost:8000/ || exit 1