FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update && apt-get install -y \
    gettext \
    nginx \
    supervisor \
    htop \
    && apt-get clean

WORKDIR /app

COPY requirements.txt .

RUN pip install wheel
RUN pip install --no-cache-dir -r requirements.txt

# Configure Nginx
RUN rm /etc/nginx/sites-enabled/default
COPY ./config/nginx/nginx.conf /etc/nginx/conf.d/

# Configure Supervisor
COPY ./config/supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY . .

# Set the entrypoint
RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

# Expose necessary ports
EXPOSE 80 443 8000 9000

# Start Supervisor to manage all processes
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# RUN python manage.py collectstatic --noinput
