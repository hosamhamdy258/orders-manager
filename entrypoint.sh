#!/bin/bash
# ===========================================
# Run the log directory creation script
python initialize_logs.py
# ===========================================



# ===========================================
# Static Files Generation in Production
# ===========================================

# echo "DJANGO_DEVELOPMENT is set to: $DJANGO_DEVELOPMENT"

# Default DJANGO_DEVELOPMENT to False if not set
DJANGO_DEVELOPMENT="${DJANGO_DEVELOPMENT:-False}"

# Define the marker file location inside the container
MARKER_FILE="/static/.collectstatic_done"

if [ "$DJANGO_DEVELOPMENT" = "False" ] && [ ! -f "$MARKER_FILE" ]; then
  echo "Running collectstatic as DJANGO_DEVELOPMENT is False and it hasn't run yet."
  # Collect static files into the container to reduce image size
  python manage.py collectstatic --clear --link --noinput
  # Create the marker file to indicate collectstatic has been run
  mkdir -p "$(dirname "$MARKER_FILE")"
  touch "$MARKER_FILE"
# else
#   echo "Skipping collectstatic (either already run or DJANGO_DEVELOPMENT is True)."
fi
# ===========================================



# ===========================================
# Environment Section
# ===========================================

# Path to the .env file
ENV_FILE="./core/settings/.env"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
  echo ".env file not found in /core/settings. Creating one with a generated SECRET_KEY."
  
  # Generate a SECRET_KEY using Python and write it to the .env file
  SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
  
  # Create the .env file and add the SECRET_KEY
  echo "DJANGO_SECRET_KEY=$SECRET_KEY" > "$ENV_FILE"
  echo "DJANGO_DEVELOPMENT=False" >> "$ENV_FILE"

# else
#   echo ".env file found in /core/settings. Skipping creation."
fi
# ===========================================



# Execute the main command (passed as CMD in Dockerfile)
exec "$@"
