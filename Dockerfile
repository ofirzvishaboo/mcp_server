FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*
# Install uv for faster package management
RUN pip install uv

# Copy requirements file
COPY requirements.txt .

# Install dependencies using uv
RUN uv venv
RUN uv pip install -r requirements.txt

# Copy application code
COPY server.py .
COPY client.py .

# Expose the port the server runs on
EXPOSE 8050

# Command to run the server
CMD ["uv", "run", "server.py"]