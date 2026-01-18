# 1. Use an official lightweight Python image
FROM python:3.13-slim

# 2. Set environment variables
# Prevents Python from writing .pyc files and ensures output is sent to logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5050

# 3. Set work directory
WORKDIR /app

# 4. Install system dependencies (none needed currently, but placeholder for future)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# 5. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the application code
COPY . .

# 7. Create the instance folder and set permissions
# This ensures SQLite has a place to live even before we map the volume
RUN mkdir -p /app/instance && chmod 777 /app/instance

# 8. Create a non-privileged user for security
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# 9. Expose the port
EXPOSE $PORT

# 10. Run the application using Gunicorn
# --bind 0.0.0.0:$PORT makes the app accessible outside the container
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "1", "--threads", "4", "--worker-class", "gthread", "run:app"]