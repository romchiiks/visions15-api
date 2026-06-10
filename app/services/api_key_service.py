import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


class ApiKeyService:
    def __init__(self, api_keys_file: str):
        self.api_keys_file = Path(api_keys_file)

    def generate_api_key(self) -> str:
        return f"lsa_{secrets.token_urlsafe(32)}"

    def hash_api_key(self, api_key: str) -> str:
        digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        return f"sha256${digest}"

    def verify_api_key(self, api_key: str) -> bool:
        data = self._read_storage()

        incoming_hash = self.hash_api_key(api_key)

        for item in data["keys"]:
            if not item.get("is_active", True):
                continue

            stored_hash = item["key_hash"]

            if hmac.compare_digest(incoming_hash, stored_hash):
                return True

        return False

    def create_key(self, name: str) -> str:
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)

        data = self._read_storage()

        data["keys"].append(
            {
                "name": name,
                "key_hash": key_hash,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
            }
        )

        self._write_storage(data)

        return api_key

    def _read_storage(self) -> dict:
        self.api_keys_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.api_keys_file.exists():
            return {"keys": []}

        with self.api_keys_file.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write_storage(self, data: dict) -> None:
        self.api_keys_file.parent.mkdir(parents=True, exist_ok=True)

        with self.api_keys_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)