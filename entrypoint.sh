#!/bin/bash

# Run the log directory creation script
python initialize_logs.py

# echo "DJANGO_DEVELOPMENT is set to: $DJANGO_DEVELOPMENT"

# Define the marker file location inside the container
MARKER_FILE="/static/.collectstatic_done"

if [ "$DJANGO_DEVELOPMENT" = "False" ] && [ ! -f "$MARKER_FILE" ]; then
  echo "Running collectstatic as DJANGO_DEVELOPMENT is False and it hasn't run yet."
  # Collect static files into the container to reduce image size
  python manage.py collectstatic --clear --link --noinput
  # Create the marker file to indicate collectstatic has been run
  mkdir -p "$(dirname "$MARKER_FILE")"
  touch "$MARKER_FILE"
else
  echo "Skipping collectstatic (either already run or DJANGO_DEVELOPMENT is True)."
fi

# Execute the main command (passed as CMD in Dockerfile)
exec "$@"
