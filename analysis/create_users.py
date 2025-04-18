import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
ANILIST_TOKEN = os.getenv("ANILIST_TOKEN")


def create_user(username: str, password: str, email: str):
    url = f"{BASE_URL}/auth/signup"
    data = {
        "username": username,
        "password": password,
        "email": email,
    }
    r = httpx.post(url, json=data)
    if r.status_code == 201:
        print(f"✅ Created user {username}")
    elif r.status_code == 400:
        print(f"⚠️  User {username} already exists")
    else:
        print(f"❌ Failed to create {username}: {r.status_code} - {r.text}")


def login_user(username: str, password: str) -> str:
    url = f"{BASE_URL}/auth/token"
    data = {
        "username": username,
        "password": password,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = httpx.post(url, data=data, headers=headers)
    r.raise_for_status()
    return r.json()["access_token"]


def link_anilist(token: str):
    url = f"{BASE_URL}/auth/anilist/link"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {"access_token": ANILIST_TOKEN}
    r = httpx.post(url, json=data, headers=headers)
    r.raise_for_status()
    print("🔗 Linked Anilist token")


def main(n: int):
    base_username = "testuser"
    base_password = "testpass123"
    domain = "example.com"

    for i in range(n):
        username = f"{base_username}{i}"
        password = base_password
        email = f"{username}@{domain}"

        try:
            create_user(username, password, email)
            token = login_user(username, password)
            link_anilist(token)
        except Exception as e:
            print(f"❌ Error for {username}: {e}")


if __name__ == "__main__":
    import sys

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    main(n)
