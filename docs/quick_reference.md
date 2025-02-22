# Quick Reference Guide

## 1. Environment Setup

### Local Development

```bash
# 1. Copy the environment template
cp server/.env.example server/.env

# 2. Set required variables in server/.env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# 3. Validate environment (fails if required vars are missing/invalid)
python server/scripts/validate_env.py
```

### Adding New Environment Variables
1. Declare the variable in your configuration code (e.g., app/core/config.py).
2. Update the .env.example file with a placeholder value.
3. Add or update tests (unit tests or validate_env checks) to ensure the variable is set and valid.
4. Document it in the quick reference or relevant docs so everyone knows how to configure it.

### Next.js Environment Injection
- Next.js automatically loads variables prefixed with `NEXT_PUBLIC_` from `.env.local` or `.env.*` files.
- Ensure that sensitive variables not meant for the browser remain unexposed by omitting the `NEXT_PUBLIC_` prefix.
- For more details, see the Next.js docs on environment variables.

## 2. Secrets Management

### Basic Principles
- Never commit actual secrets (like .env files) to version control.
- Use .env.example as a template for local development.
- For production, store secrets in GitHub Actions Secrets or a secure vault (e.g., HashiCorp Vault, AWS Parameter Store).
- Rotate secrets regularly to reduce risk.
- **IMPORTANT:** Avoid logging secrets or including them in error messages. If you must log something, obfuscate or mask sensitive values.

### Rotating Secrets
1. Generate a new secret:
```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

2. Update GitHub Actions (if using GitHub for CI/CD):
   - Go to Settings > Secrets in your repository.
   - Update the relevant secret (e.g., SECRET_KEY, DATABASE_PASSWORD).
   - Trigger a test workflow to confirm everything is functioning.

3. Update Production:
   - Add the new secret to your production environment.
   - Verify in a staging environment first.
   - Roll out changes with zero downtime to avoid disruptions.

### Local Secrets
- Keep personal .env files out of version control.
- Store your local secrets in a password manager or encrypted storage.
- Rely on .env.example to see which variables are required.

## 3. Common Tasks

### Database Migrations
```bash
# Generate a new migration script
alembic revision -m "Add new table or column"

# Apply all pending migrations
alembic upgrade head

# Downgrade if necessary
alembic downgrade -1
```

Ensure your alembic.ini points to the correct database:
```ini
[alembic]
script_location = migrations

[database]
sqlalchemy.url = postgresql://user:pass@localhost:5432/db
```

**Tip:** Always validate environment variables (especially DATABASE_URL) before running migrations.

### Running Tests

```bash
# Run all Python tests
pytest

# Run with coverage
pytest --cov=app

# Test environment validation
python server/scripts/validate_env.py
```

### Multi-Environment Testing
```bash
# Run tests in specific environment
ENVIRONMENT=staging pytest

# Run with custom environment file
ENV_FILE=.env.staging pytest
```

- Integrate these tests into your CI/CD pipeline so that each commit or pull request is validated automatically.
- Use environment-specific configurations for different stages (dev, staging, prod).

### Container Operations

```bash
# Spin up containers for local development
docker-compose up -d

# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Environment variables can be passed to containers via:
- `.env` file in the same directory as docker-compose.yml
- Environment-specific override files (e.g., docker-compose.override.yml)
- Direct environment variable injection in CI/CD

### Feature Flags

#### Backend (Python)
```python
from app.core.config import settings

if settings.FEATURE_AUTH_2FA_ENABLED:
    # 2FA logic here
    def enable_2fa(user_id: str) -> bool:
        # Implementation
        pass
```

#### Frontend (Next.js / React)
```javascript
import { useFeatureFlag } from '@/hooks/useFeatureFlag';

function TwoFactorFeature() {
  const is2FAEnabled = useFeatureFlag('AUTH_2FA_ENABLED');
  return is2FAEnabled ? <TwoFactorSetup /> : null;
}
```

## 4. Best Practices

- **Validate Environment at Startup:** Use scripts (e.g., validate_env.py) to catch missing or malformed variables before the app fully boots.
- **Use a Consistent Naming Convention:** e.g., APP_ENV, DATABASE_URL, SECURITY_JWT_KEY, FEATURE_X_ENABLED.
- **Document Everything:** Update .env.example, config docs, and any relevant READMEs or wikis whenever you add or modify environment variables.
- **Secure Logging:** Never log secrets or sensitive data. Use masking or redaction if sensitive values must be referenced.
- **CI/CD Integration:**
  - Add environment validation checks in your GitHub Actions (or other CI) pipeline.
  - Use secrets management (GitHub Actions Secrets, vaults, etc.) to avoid exposing credentials.
  - Automate tests, container builds, and security scans to catch issues early.

## 5. Troubleshooting

### Environment Validation Fails
- Confirm you have a .env file with all required variables.
- Check for typos or incorrect formatting (e.g., missing quotes, invalid URL schemes).
- Run `python server/scripts/validate_env.py` to see the exact error.

### Secrets Access Denied
- Verify that your CI/CD pipeline or local environment has permission to read the secret.
- Ensure the secret name in GitHub Actions matches the reference in your code or Docker Compose.
- If rotating secrets, confirm you updated them everywhere (local, staging, production).

### Container Issues
- Check container logs (`docker logs <container_name>`) for environment or startup errors.
- Validate Docker configuration in docker-compose.yml or .prod.yml.
- Confirm that secrets are passed correctly into your container environment.

### Database Migration Errors
- Confirm your DATABASE_URL is set properly in your environment or .env file.
- Check if the alembic config points to the correct database.
- Ensure your migrations are up to date with `alembic upgrade head`.

### Feature Flag Not Working
- Ensure the environment variable for the flag is set.
- Verify both backend and frontend read the same flag name.
- Double-check you're running the correct environment (dev vs. staging vs. production).

## 6. Test Environment Setup

### Overview
This project uses a dedicated test database and environment configuration for running tests. By separating test resources from development or production, we avoid data conflicts and ensure clean, repeatable test suites.

### Environment Configuration

#### 1. Environment Files
The project uses `.env.test` for test-specific configuration:
```bash
# Database Configuration
POSTGRES_USER=app_user
POSTGRES_PASSWORD=app_password
POSTGRES_DB=jsquared_test
POSTGRES_SERVER=postgres
POSTGRES_PORT=5432

# Server & CORS Configuration
ALLOWED_HOSTS=["localhost","127.0.0.1"]
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# Logging Configuration
LOGGING_FORMAT=json
```

#### 2. Docker Configuration
Our `docker-compose.yml` is configured to load both `.env` and `.env.test`:
```yaml
services:
  server:
    env_file:
      - server/.env
      - server/.env.test
```

### Database Setup

#### 1. Database Initialization
- PostgreSQL initialization scripts in `docker/postgres/initdb/` automatically create:
  - Main database (`jsquared`)
  - Test database (`jsquared_test`)
  - Application user with appropriate permissions

#### 2. Test Database Management
- Each test session starts with a clean database state
- Tables are created/dropped automatically via pytest fixtures
- Transactions are rolled back after each test

### Running Tests

#### 1. Start the Environment
```bash
docker compose up -d
```

#### 2. Run Test Suite
```bash
# Run all tests
docker compose exec server pytest tests/ -v

# Run specific test file
docker compose exec server pytest tests/models/test_user.py -v

# Run with coverage
docker compose exec server pytest tests/ --cov=app -v
```

#### 3. Verify Environment
```bash
# Check environment variables
docker compose exec server env | grep POSTGRES

# Check database connection
docker compose exec postgres psql -U app_user -d jsquared_test -c "\l"
```

### Test Infrastructure

#### 1. Test Database Fixtures
Located in `tests/conftest.py`:
```python
@pytest.fixture(scope="session")
def test_db_url():
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

@pytest.fixture(scope="session")
async def test_engine(test_db_url):
    engine = create_async_engine(test_db_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
```

### Security Considerations
- Test credentials are separate from production
- Environment files are properly gitignored
- CORS settings are configured for test environment only
- JSON logging ensures structured, parseable logs
- Sensitive data is excluded from logs

### Troubleshooting
1. Database Connection Issues
   - Verify PostgreSQL container is running: `docker compose ps`
   - Check database logs: `docker compose logs postgres`
   - Confirm environment variables: `docker compose exec server env | grep POSTGRES`

2. Test Failures
   - Check test database state: `docker compose exec postgres psql -U app_user -d jsquared_test`
   - Review test logs for JSON formatting
   - Verify CORS settings if running integration tests

## 7. Getting Help

- **Project Documentation:** Consult `/docs` or any internal wiki pages for deeper explanations.
- **CI/CD Logs:** Check your GitHub Actions (or other CI) logs to see if validations or tests are failing.
- **DevOps Team:** For production or infrastructure-related issues, coordinate with the DevOps/SRE team.
- **Security Team:** If you suspect a secret leak or have questions about rotating credentials, involve the Security Engineer immediately.
- **Frontend Team:** For Next.js environment variable usage or feature flag integration, contact the Senior Frontend Developer.
