"""Test Redis Sentinel security configuration."""

import logging
import os
import time
from typing import Any, Dict

import redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class RedisSentinelSecurityTester:
    """Test Redis Sentinel security configuration."""

    def __init__(self):
        """Initialize the tester with configuration from environment."""
        self.redis_password = os.getenv("REDIS_PASSWORD", "secure_redis_password_test")
        self.master_port = int(os.getenv("REDIS_MASTER_PORT", "6379"))
        self.replica_port = int(os.getenv("REDIS_REPLICA_1_PORT", "6380"))
        self.sentinel_port = int(os.getenv("REDIS_SENTINEL_1_PORT", "26379"))
        self.master_name = os.getenv("REDIS_MASTER_NAME", "mymaster")

    def check_redis_info(self, client: redis.Redis, node_type: str) -> Dict[str, Any]:
        """Get Redis INFO command output with error handling."""
        try:
            info = client.info()
            logging.info(f"{node_type} connection successful")
            return info
        except redis.AuthenticationError as e:
            logging.error(f"{node_type} authentication failed: {e}")
            return {}
        except Exception as e:
            logging.error(f"{node_type} connection error: {e}")
            return {}

    def test_master_security(self) -> bool:
        """Test master node security configuration."""
        master = redis.Redis(
            host="localhost",
            port=self.master_port,
            password=self.redis_password,
            decode_responses=True,
        )
        info = self.check_redis_info(master, "Master")
        if not info:
            return False

        if info.get("role") != "master":
            logging.error("Node is not in master role")
            return False

        logging.info("Master security verification passed")
        return True

    def test_replica_security(self) -> bool:
        """Test replica node security configuration."""
        replica = redis.Redis(
            host="localhost",
            port=self.replica_port,
            password=self.redis_password,
            decode_responses=True,
        )
        info = self.check_redis_info(replica, "Replica")
        if not info:
            return False

        if info.get("role") != "slave":
            logging.error("Node is not in replica role")
            return False

        if info.get("master_link_status") != "up":
            logging.error("Replica is not connected to master")
            return False

        logging.info("Replica security verification passed")
        return True

    def test_sentinel_security(self) -> bool:
        """Test sentinel security configuration."""
        try:
            sentinel = redis.Sentinel(
                [("localhost", self.sentinel_port)],
                sentinel_kwargs={"password": self.redis_password},
                password=self.redis_password,
            )
            master = sentinel.discover_master(self.master_name)
            if not master:
                logging.error("Sentinel unable to discover master")
                return False

            logging.info(f"Sentinel discovered master at {master}")
            return True
        except Exception as e:
            logging.error(f"Sentinel verification failed: {e}")
            return False

    def run_all_tests(self) -> bool:
        """Run all security tests."""
        logging.info("Starting Redis Sentinel security tests...")

        master_ok = self.test_master_security()
        replica_ok = self.test_replica_security()
        sentinel_ok = self.test_sentinel_security()

        all_passed = all([master_ok, replica_ok, sentinel_ok])
        if all_passed:
            logging.info("All security tests passed successfully!")
        else:
            logging.error("Some security tests failed")

        return all_passed


def main():
    """Main entry point for security testing."""
    tester = RedisSentinelSecurityTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
