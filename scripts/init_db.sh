#!/bin/bash

# Database configuration
DB_NAME="jsquared"
DB_USER="postgres"
DB_PASSWORD="postgres"

# Create database if it doesn't exist
PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME"

echo "Database '$DB_NAME' is ready."
