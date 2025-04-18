import os
from dotenv import load_dotenv
import httpx
from rich import print

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

response = httpx.post(
    f"{BASE_URL}/auth/token",
    data={"username": USERNAME, "password": PASSWORD},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
response.raise_for_status()
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_current_user() -> dict:
    response = httpx.get(f"{BASE_URL}/auth/users/me", headers=headers)
    response.raise_for_status()
    return response.json()


def link_anilist_account(access_token: str):
    response = httpx.post(
        f"{BASE_URL}/auth/anilist/link",
        headers=headers,
        json={"access_token": access_token},
    )
    response.raise_for_status()
    return response.json()


def test_anilist_account():
    response = httpx.get(f"{BASE_URL}/auth/anilist/test", headers=headers)
    response.raise_for_status()
    return response.json()


def get_watchlist():
    response = httpx.get(f"{BASE_URL}/watchlist/", headers=headers, timeout=20.0)
    response.raise_for_status()
    return response.json()


def get_torrents():
    response = httpx.get(f"{BASE_URL}/torrents/", headers=headers)
    response.raise_for_status()
    return response.json()


def download(media_id: int, ep_num: int):
    response = httpx.post(
        f"{BASE_URL}/watchlist/download",
        headers=headers,
        json={"media_id": media_id, "episode": ep_num, "preferred_quality": "1080p"},
    )
    response.raise_for_status()
    return response.json()


def pause_torrent(info_hash: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = httpx.post(
        f"{BASE_URL}/torrents/{info_hash}/pause",
        data={"info_hash": info_hash},
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


def resume_torrent(info_hash: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = httpx.post(
        f"{BASE_URL}/torrents/{info_hash}/resume",
        data={"info_hash": info_hash},
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


def delete_torrent(info_hash: str):
    response = httpx.request(
        "DELETE",
        f"{BASE_URL}/torrents/{info_hash}",
        data={"info_hash": info_hash, "delete_files": "true"},
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


def set_progress(media_id: int, progress: int):
    response = httpx.post(
        f"{BASE_URL}/watchlist/progress",
        headers=headers,
        json={"media_id": media_id, "progress": progress},
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    try:
        res = get_watchlist()
        print(res)
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"Error: {e}")
