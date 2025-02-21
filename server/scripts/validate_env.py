#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings, EnvironmentType

def validate_environment():
    """Validate environment variables at startup."""
    try:
        settings = Settings()
        
        # Additional production-specific validations
        if settings.ENVIRONMENT == EnvironmentType.PRODUCTION:
            settings.validate_production_settings()
            
        print("✅ Environment validation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Environment validation failed: {str(e)}")
        return False

if __name__ == "__main__":
    if not validate_environment():
        sys.exit(1)
