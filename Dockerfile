# Use the official Python 3.11.4 image from the Docker Hub
FROM python:3.11.4-slim

# Set the working directory in the container
WORKDIR /
# Install system dependencies required for WeasyPrint

RUN apt-get update && apt-get install -y \
    build-essential \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libpq-dev \
    libxml2 \
    libxslt1.1 \
    libjpeg-dev \
    zlib1g-dev \
    libpangocairo-1.0-0 \
    fonts-liberation \
    fonts-dejavu \
    wget \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
# Copy the requirements.txt file into the container at /
COPY requirements.txt /

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /

# Expose the port that the FastAPI app runs on
EXPOSE 8000

# Command to run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]