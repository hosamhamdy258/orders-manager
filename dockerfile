FROM python:3.10.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y gettext

WORKDIR /app

COPY requirements.txt .

RUN pip install wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# RUN python manage.py collectstatic --noinput

# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
