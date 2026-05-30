FROM python:3.9-slim

RUN groupadd -r app && useradd -r -g app app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

ENV APP_COLOR=blue 

RUN chown -R app:app /app
USER app

RUN sed -i 's/8501/8000/g' app.py

EXPOSE 8000

CMD ["python", "app.py"]

HEALTHCHECK CMD curl -f http://localhost:8000/ || exit 1