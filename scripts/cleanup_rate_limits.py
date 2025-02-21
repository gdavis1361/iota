#!/usr/bin/env python3
"""
Script to clean up expired rate limit metrics and perform maintenance tasks.
"""

import argparse
import logging
import sys
import time
from typing import List, Set
import redis
from prometheus_client import CollectorRegistry, write_to_textfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('rate_limit_cleanup')

class RateLimitCleaner:
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: str = None,
        redis_db: int = 0,
        dry_run: bool = False
    ):
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=redis_db,
            decode_responses=True
        )
        self.dry_run = dry_run
        self.metrics_registry = CollectorRegistry()

    def cleanup_expired_windows(self) -> int:
        """Clean up expired rate limit windows"""
        now = time.time()
        pattern = "rate_limit:*"
        cleaned = 0
        
        try:
            # Scan for rate limit keys
            for key in self.redis.scan_iter(pattern):
                try:
                    # Check if window has any active members
                    if self.redis.zcount(key, float('-inf'), now) == 0:
                        if not self.dry_run:
                            self.redis.delete(key)
                        cleaned += 1
                        logger.info(f"Cleaned up expired window: {key}")
                except redis.RedisError as e:
                    logger.error(f"Error cleaning up key {key}: {e}")
                    continue
        except redis.RedisError as e:
            logger.error(f"Error scanning Redis keys: {e}")
            return 0

        return cleaned

    def aggregate_metrics(self) -> None:
        """Aggregate high-cardinality metrics"""
        now = time.time()
        pattern = "rate_limit:*"
        aggregated = {
            "violations_total": 0,
            "failed_logins_total": 0
        }

        try:
            # Aggregate metrics
            for key in self.redis.scan_iter(pattern):
                if ":login_attempts" in key:
                    count = self.redis.zcount(key, float('-inf'), now)
                    aggregated["failed_logins_total"] += count
                else:
                    count = self.redis.zcount(key, float('-inf'), now)
                    aggregated["violations_total"] += count

            # Write aggregated metrics
            if not self.dry_run:
                self._write_aggregated_metrics(aggregated)
            
            logger.info(f"Aggregated metrics: {aggregated}")
        except redis.RedisError as e:
            logger.error(f"Error aggregating metrics: {e}")

    def _write_aggregated_metrics(self, metrics: dict) -> None:
        """Write aggregated metrics to file"""
        try:
            write_to_textfile(
                '/var/lib/prometheus/rate_limit_aggregated.prom',
                self.metrics_registry
            )
            logger.info("Wrote aggregated metrics to file")
        except Exception as e:
            logger.error(f"Error writing metrics file: {e}")

    def compress_windows(self) -> None:
        """Compress rate limit windows to save memory"""
        now = time.time()
        pattern = "rate_limit:*"

        try:
            for key in self.redis.scan_iter(pattern):
                # Remove all entries older than the window
                if not self.dry_run:
                    self.redis.zremrangebyscore(key, float('-inf'), now - 3600)
                logger.info(f"Compressed window for key: {key}")
        except redis.RedisError as e:
            logger.error(f"Error compressing windows: {e}")

    def run_maintenance(self) -> None:
        """Run all maintenance tasks"""
        try:
            # Clean up expired windows
            cleaned = self.cleanup_expired_windows()
            logger.info(f"Cleaned up {cleaned} expired windows")

            # Aggregate metrics
            self.aggregate_metrics()
            logger.info("Completed metrics aggregation")

            # Compress windows
            self.compress_windows()
            logger.info("Completed window compression")

        except Exception as e:
            logger.error(f"Error during maintenance: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(
        description='Clean up expired rate limit metrics'
    )
    parser.add_argument(
        '--redis-host',
        default='localhost',
        help='Redis host'
    )
    parser.add_argument(
        '--redis-port',
        type=int,
        default=6379,
        help='Redis port'
    )
    parser.add_argument(
        '--redis-password',
        help='Redis password'
    )
    parser.add_argument(
        '--redis-db',
        type=int,
        default=0,
        help='Redis database number'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode'
    )

    args = parser.parse_args()

    try:
        cleaner = RateLimitCleaner(
            redis_host=args.redis_host,
            redis_port=args.redis_port,
            redis_password=args.redis_password,
            redis_db=args.redis_db,
            dry_run=args.dry_run
        )

        cleaner.run_maintenance()
        logger.info("Maintenance completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Maintenance failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
