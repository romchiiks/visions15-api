import hashlib
import hmac
import json
import os
import secrets
import tempfile
from contextlib import contextmanager
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

        with self._storage_lock():
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

        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.api_keys_file.parent,
            prefix=f".{self.api_keys_file.name}.",
            suffix=".tmp",
            delete=False,
        )
        temp_path = Path(temp_file.name)

        try:
            with temp_file as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            os.replace(temp_path, self.api_keys_file)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    @contextmanager
    def _storage_lock(self):
        self.api_keys_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.api_keys_file.with_suffix(f"{self.api_keys_file.suffix}.lock")

        with lock_file.open("a+b") as file:
            self._lock_file(file)
            try:
                yield
            finally:
                self._unlock_file(file)

    def _lock_file(self, file) -> None:
        if os.name == "nt":
            import msvcrt

            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, 1)
            return

        import fcntl

        fcntl.flock(file.fileno(), fcntl.LOCK_EX)

    def _unlock_file(self, file) -> None:
        if os.name == "nt":
            import msvcrt

            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
