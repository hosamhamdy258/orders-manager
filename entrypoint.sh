#!/bin/bash

# Run the log directory creation script
python initialize_logs.py

# Execute the main command
exec "$@"
