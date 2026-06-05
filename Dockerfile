FROM python:3.11-slim

WORKDIR /app

# Install basic system requirements
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend/ ./backend
COPY frontend/ ./frontend
COPY policy_terms.json .
COPY adjudication_rules.md .
COPY test_cases.json .
COPY README.md .

# Create uploads and DB directories with open permissions (necessary for Hugging Face non-root users)
RUN mkdir -p uploads backend/database && chmod -R 777 uploads backend/database

# Copy and setup start script
COPY start.sh .
RUN chmod +x start.sh

# Expose ports for documentation/port mapping
EXPOSE 8000
EXPOSE 7860

# Set default env variable pointing to local container backend
ENV BACKEND_URL=http://127.0.0.1:8000

# Start both services
CMD ["./start.sh"]
