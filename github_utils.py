import base64
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

if not GITHUB_TOKEN or not GITHUB_REPO:
    raise ValueError("GITHUB_TOKEN and GITHUB_REPO must be set in .env")

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"}
BASE_URL = "https://api.github.com/repos"


def read_json(path):
    """Read a JSON file from the GitHub repo. Returns (data, sha)."""
    url = f"{BASE_URL}/{GITHUB_REPO}/contents/{path}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    payload = r.json()
    content = base64.b64decode(payload["content"]).decode("utf-8")
    return json.loads(content), payload["sha"]


def write_json(path, data, sha, message):
    """Write a JSON file to the GitHub repo."""
    url = f"{BASE_URL}/{GITHUB_REPO}/contents/{path}"
    encoded = base64.b64encode(json.dumps(data, indent=2, ensure_ascii=False).encode()).decode()
    body = {"message": message, "content": encoded, "sha": sha}
    r = requests.put(url, json=body, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def write_html(path, html_content, sha, message):
    """Write an HTML file to the GitHub repo. sha can be empty string for first create."""
    url = f"{BASE_URL}/{GITHUB_REPO}/contents/{path}"
    encoded = base64.b64encode(html_content.encode("utf-8")).decode()
    body = {"message": message, "content": encoded}
    if sha:
        body["sha"] = sha
    r = requests.put(url, json=body, headers=HEADERS)
    r.raise_for_status()
    return r.json()
