FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update && apt-get install -y \
    gettext \
    && apt-get clean

WORKDIR /app

COPY requirements.txt .

RUN pip install wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose necessary ports
EXPOSE 80 443 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
