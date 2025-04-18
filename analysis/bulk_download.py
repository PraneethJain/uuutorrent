import os
import asyncio
import time
import logging
from dotenv import load_dotenv
import httpx

load_dotenv()
BASE_URL = os.getenv("BASE_URL")

tmp_logger = logging.getLogger()
tmp_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
tmp_logger.addHandler(handler)
logger = tmp_logger


async def download(client: httpx.AsyncClient, username: str, password: str) -> dict:
    """
    Authenticate and download a watchlist item for a given user.
    """
    response = await client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()
    token = response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = await client.post(
        "/watchlist/download",
        headers=headers,
        json={"media_id": 175443, "episode": 8, "preferred_quality": "1080p"},
    )
    response.raise_for_status()
    return response.json()


async def main(n: int):
    base_username = "testuser"
    base_password = "testpass123"

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        tasks = []
        for i in range(n):
            username = f"{base_username}{i}"
            password = base_password
            tasks.append(download(client, username, password))

        start_time = time.monotonic()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.monotonic() - start_time

        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Request {idx} failed: {result}")
            else:
                logger.info(f"Request {idx} succeeded: {result}")

        logger.info(f"Total time for {n} requests: {total_time:.2f} seconds")


if __name__ == "__main__":
    import sys

    try:
        n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    except ValueError:
        logger.error("Please provide an integer for the number of requests.")
        sys.exit(1)

    asyncio.run(main(n))
