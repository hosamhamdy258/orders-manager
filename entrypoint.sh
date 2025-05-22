#!/bin/bash

set -e

# Default DJANGO_DEVELOPMENT to False if not set
DJANGO_DEVELOPMENT="${DJANGO_DEVELOPMENT:-False}"

if [ "$DJANGO_DEVELOPMENT" = "False" ]; then
	# ===========================================
	# Run the log directory creation script
	python initialize_logs.py
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
		echo "DJANGO_SECRET_KEY=$SECRET_KEY" >"$ENV_FILE"
		echo "DJANGO_DEVELOPMENT=False" >>"$ENV_FILE"

	# else
	#   echo ".env file found in /core/settings. Skipping creation."
	fi
	# ===========================================

	# ===========================================
	# Static Files Generation in Production
	# ===========================================

	# echo "DJANGO_DEVELOPMENT is set to: $DJANGO_DEVELOPMENT"

	# Define the marker file location inside the container
	MARKER_FILE="/run/.collectstatic_done"

	if [ ! -f "$MARKER_FILE" ]; then
		echo "Running collectstatic as DJANGO_DEVELOPMENT is False and it hasn't run yet."
		# Collect static files into the container to reduce image size
		rm -rf ./static
		python manage.py collectstatic --link --noinput
		# Create the marker file to indicate collectstatic has been run
		mkdir -p "$(dirname "$MARKER_FILE")"
		touch "$MARKER_FILE"
	# else
	#   echo "Skipping collectstatic (either already run or DJANGO_DEVELOPMENT is True)."
	fi
	# ===========================================

	# ===========================================
	# Migrations Files Generation in Production
	# ===========================================

	MARKER_FILE="/run/.migrations_done"
	APPS_FILE="apps.txt"

	if [ -f "$APPS_FILE" ] && [ ! -f "$MARKER_FILE" ]; then
		echo "Running migrations as marker not found and apps list present."
		mapfile -t APPS < <(grep -vE '^\s*(#|$)' "$APPS_FILE")

		if [ ${#APPS[@]} -eq 0 ]; then
			echo "No apps found in $APPS_FILE; skipping makemigrations."
		else
			printf 'Making migrations for apps: %s\n' "${APPS[*]}"
			python manage.py makemigrations "${APPS[@]}"
		fi

		python manage.py migrate
		mkdir -p "$(dirname "$MARKER_FILE")"
		touch "$MARKER_FILE"
		echo "Migrations complete; marker file created at $MARKER_FILE."
	fi

	# ===========================================

	# ===========================================
	# Self-Signed SSL Certificate Creation Section
	# ===========================================

	# Define paths for SSL certificate and key
	SSL_CERT_DIR="/ssl"
	SSL_CERT_FILE="$SSL_CERT_DIR/server.crt"
	SSL_KEY_FILE="$SSL_CERT_DIR/server.key"

	# Ensure the SSL directory exists
	if [ ! -d "$SSL_CERT_DIR" ]; then
		echo "Creating SSL directory at $SSL_CERT_DIR."
		mkdir -p "$SSL_CERT_DIR"
	fi

	# Check if the SSL certificate and key exist
	if [ ! -f "$SSL_CERT_FILE" ] || [ ! -f "$SSL_KEY_FILE" ]; then
		# echo "SSL certificate or key not found. Generating self-signed certificate for testing purposes."

		# Generate a self-signed SSL certificate using OpenSSL
		openssl req -x509 -newkey rsa:4096 -keyout "$SSL_KEY_FILE" -out "$SSL_CERT_FILE" -days 30 -nodes -subj "/CN=localhost"

		echo "Self-signed SSL certificate and key have been generated:"
		echo "  Certificate: $SSL_CERT_FILE"
		echo "  Key: $SSL_KEY_FILE"
	# else
	#   echo "SSL certificate and key already exist. Skipping generation."
	fi
# ===========================================

fi

# Execute the main command (passed as CMD in Dockerfile)
exec "$@"
