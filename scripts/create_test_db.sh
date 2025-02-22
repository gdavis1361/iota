#!/bin/bash

# Create test database
psql -U postgres -c "DROP DATABASE IF EXISTS test_db;"
psql -U postgres -c "CREATE DATABASE test_db;"
