FROM python:3.12-slim

# Create a non-root user
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app

# Copy dependency manifests
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy source
COPY . .

# Expose the port
EXPOSE 8000

# Switch to non-root user
USER app

# Set the command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]

# Add a healthcheck
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD curl -f http://localhost:8000/ || exit 1