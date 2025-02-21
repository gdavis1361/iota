-- Create test database
CREATE DATABASE test_db;

-- Create application user
CREATE USER app_user WITH PASSWORD 'app_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE jsquared TO app_user;
GRANT ALL PRIVILEGES ON DATABASE test_db TO app_user;
