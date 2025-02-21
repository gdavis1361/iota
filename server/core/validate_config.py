#!/usr/bin/env python3
"""
Configuration validation CLI tool.

Usage:
    python validate_config.py [--env ENV_FILE]
"""
import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Optional

from pydantic import ValidationError
from pydantic_settings import SettingsError

from server.core.config import Settings, get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_env_file(env_file: Optional[str] = None) -> Dict[str, str]:
    """Load environment variables from file."""
    if env_file:
        env_path = Path(env_file)
        if not env_path.exists():
            logger.error(f"Environment file not found: {env_file}")
            sys.exit(1)
        
        # Load environment file
        env_vars = {}
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        # Update environment
        os.environ.update(env_vars)
        return env_vars
    
    return dict(os.environ)

def validate_configuration(env_vars: Dict[str, str]) -> None:
    """Validate configuration settings."""
    try:
        # Force refresh of settings with current environment
        settings = get_settings(refresh=True)
        
        # Log successful validation
        logger.info("Configuration validation successful!")
        logger.info("Current configuration:")
        logger.info(f"  Environment: {settings.ENVIRONMENT}")
        logger.info(f"  Debug Mode: {settings.DEBUG}")
        logger.info(f"  Log Level: {settings.LOG_LEVEL}")
        logger.info(f"  Allowed Hosts: {settings.ALLOWED_HOSTS}")
        
        if settings.SENTRY_ENABLED:
            logger.info("Sentry Configuration:")
            logger.info(f"  Environment: {settings.SENTRY_ENVIRONMENT}")
            logger.info(f"  Debug Mode: {settings.SENTRY_DEBUG}")
            logger.info(f"  Traces Sample Rate: {settings.SENTRY_TRACES_SAMPLE_RATE}")
            logger.info(f"  Profiles Sample Rate: {settings.SENTRY_PROFILES_SAMPLE_RATE}")
        
        logger.info("Performance Settings:")
        logger.info(f"  Slow Request Threshold: {settings.SLOW_REQUEST_THRESHOLD_MS}ms")
        logger.info(f"  Error Rate Threshold: {settings.ERROR_RATE_THRESHOLD}")
        logger.info(f"  Slow Rate Threshold: {settings.SLOW_RATE_THRESHOLD}")
        
    except ValidationError as e:
        logger.error("Configuration validation failed!")
        for error in e.errors():
            logger.error(f"  - {error['loc'][0]}: {error['msg']}")
        sys.exit(1)
    except SettingsError as e:
        logger.error(f"Settings error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate application configuration")
    parser.add_argument(
        "--env",
        help="Path to environment file",
        default=None
    )
    
    args = parser.parse_args()
    env_vars = load_env_file(args.env)
    validate_configuration(env_vars)

if __name__ == "__main__":
    main()
