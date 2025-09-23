# Simplified Dockerfile for Cascabel Border Crossing Simulation

FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy all source code
COPY . .

# Expose ports
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["python", "api/main.py"]