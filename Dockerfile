FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install production dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variable for Flask
ENV FLASK_APP=app.py

# Use environment variable for port binding
ENV PORT=8080

# Make sure the application listens on the port specified by Cloud Run
CMD exec gunicorn --bind :$PORT app:app
