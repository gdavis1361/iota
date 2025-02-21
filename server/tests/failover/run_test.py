import asyncio

from test_failover_metrics import test_failover_with_monitoring


async def main():
    await test_failover_with_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
