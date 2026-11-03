"""
Admin-only authentication.

Admin accounts live in data/admins.json with salted password hashes
(werkzeug's scrypt/pbkdf2). Default accounts are created on first run.

Change or add an admin from the project folder:
    python -m utils.auth <username> <new-password> ["Display Name"]
"""

import json
import os
import secrets
import sys

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMINS_FILE = os.path.join(BASE_DIR, "data", "admins.json")
SECRET_FILE = os.path.join(BASE_DIR, "data", ".secret_key")

# Demo credentials, created only when data/admins.json does not exist yet.
DEFAULT_ADMINS = [
    {"username": "admin", "password": "CrimeGraph@2026", "name": "System Administrator", "rank": "Admin"},
    {"username": "sp.crime", "password": "SPCrime@2026", "name": "SP Crime Branch", "rank": "Superintendent of Police"},
]


def _load():
    if not os.path.exists(ADMINS_FILE):
        admins = [{
            "username": a["username"],
            "password_hash": generate_password_hash(a["password"]),
            "name": a["name"],
            "rank": a["rank"],
            "role": "admin",
        } for a in DEFAULT_ADMINS]
        _save(admins)
        return admins
    with open(ADMINS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(admins):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(admins, f, indent=2)


def authenticate(username, password):
    """Return the admin's public profile if the credentials are valid, else None."""
    username = (username or "").strip().lower()
    for a in _load():
        if a["username"] == username and a.get("role") == "admin" and check_password_hash(a["password_hash"], password or ""):
            initials = "".join(w[0] for w in a["name"].split()[:2]).upper()
            return {"username": a["username"], "name": a["name"], "rank": a.get("rank", ""), "initials": initials}
    return None


def set_password(username, password, name=None):
    admins = _load()
    for a in admins:
        if a["username"] == username:
            a["password_hash"] = generate_password_hash(password)
            if name:
                a["name"] = name
            break
    else:
        admins.append({"username": username, "password_hash": generate_password_hash(password),
                       "name": name or username, "rank": "Admin", "role": "admin"})
    _save(admins)


def secret_key():
    """Session signing key: env var, else a random key stored once in data/.secret_key."""
    if os.environ.get("CRIMEGRAPH_SECRET_KEY"):
        return os.environ["CRIMEGRAPH_SECRET_KEY"]
    if not os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "w") as f:
            f.write(secrets.token_hex(32))
    with open(SECRET_FILE) as f:
        return f.read().strip()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    set_password(sys.argv[1].lower(), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(f"Admin '{sys.argv[1].lower()}' saved.")
