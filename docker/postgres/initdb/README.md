# PostgreSQL Initialization Scripts

This directory contains initialization scripts that run when the PostgreSQL container first starts up. Scripts are executed in alphabetical order.

## Scripts

- `00-create-databases.sql`: Creates the main and test databases, sets up the application user, and grants necessary permissions
- `01-schema.sql`: (To be created by Alembic migrations) Creates the database schema
- `02-seed-data.sql`: (Optional) Adds initial data for development

## Environment Variables

The following environment variables are used:
- `POSTGRES_USER`: Superuser username (default: postgres)
- `POSTGRES_PASSWORD`: Superuser password
- `POSTGRES_DB`: Default database (default: postgres)

## Application Database Details

### Main Database
- Name: jsquared
- User: app_user
- Password: app_password (for development only)

### Test Database
- Name: jsquared_test
- User: app_user
- Password: app_password (for development only)

## Notes
- These scripts only run when the container is first created
- For schema updates, use Alembic migrations
- Never store production credentials in these files
