#!/bin/bash

# Exit on error
set -e

# Configuration
DB_NAME="jsquared_test"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_HOST="localhost"

echo "Dropping database if it exists..."
psql -h $DB_HOST -U $DB_USER -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME';" || true
psql -h $DB_HOST -U $DB_USER -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" || true

echo "Creating database..."
psql -h $DB_HOST -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;"

echo "Setting up permissions..."
psql -h $DB_HOST -U $DB_USER -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "Test database setup complete!"
