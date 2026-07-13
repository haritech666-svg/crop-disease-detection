# Base image — Python 3.12 slim
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for faster builds)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into container
COPY . .

# Expose port 5000
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]