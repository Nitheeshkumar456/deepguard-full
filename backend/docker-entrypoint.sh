#!/bin/sh
set -e

echo "=== DeepGuard AI Backend Starting ==="

# Run database migrations
echo "Applying database migrations with Alembic..."
alembic upgrade head

echo "Database migrations applied successfully."

# Execute main command
exec "$@"
