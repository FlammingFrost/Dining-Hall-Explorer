# Use the official Python image
FROM python:3.9

# Set working directory
WORKDIR /app

# Install system dependencies (including tzdata for timezone settings)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3 \
    libgconf-2-4 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set Time Zone to PST (America/Los_Angeles)
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set environment variables for Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver
ENV PORT=8080

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Start FastAPI on port 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]