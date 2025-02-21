-- Create application user with password
CREATE USER app_user WITH PASSWORD 'app_password';

-- Create main database
CREATE DATABASE jsquared;
\c jsquared
ALTER DATABASE jsquared OWNER TO app_user;
GRANT ALL PRIVILEGES ON DATABASE jsquared TO app_user;

-- Create test database
CREATE DATABASE jsquared_test;
\c jsquared_test
ALTER DATABASE jsquared_test OWNER TO app_user;
GRANT ALL PRIVILEGES ON DATABASE jsquared_test TO app_user;

-- Grant schema creation rights
ALTER USER app_user CREATEDB;
