FROM python:3.10-slim

# Set environment variables
# Ensure that Python output is flushed immediately
ENV PYTHONUNBUFFERED 1
# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1

# Install necessary packages
RUN apt-get update && apt-get install -y \
    gettext \
    nginx \
    supervisor \
    htop \
    nano \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory for the application
WORKDIR /app

# Copy the requirements file for Python dependencies
COPY requirements.txt .

# Install the wheel package for building wheels
RUN pip install wheel
# Install Python dependencies without cache
RUN pip install --no-cache-dir -r requirements.txt

# Configure Nginx
RUN rm /etc/nginx/sites-enabled/default
COPY ./config/nginx/nginx.conf /etc/nginx/conf.d/

# Configure Supervisor
COPY ./config/supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy the entire application code into the container
COPY . .

# Set the entrypoint script and make it to be executable
RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

# Expose necessary ports
EXPOSE 80 443 8000 9000

# Start Supervisor to manage all processes
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# Start Django Development Server
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

