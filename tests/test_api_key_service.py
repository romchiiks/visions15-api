import json

from app.services.api_key_service import ApiKeyService


def test_create_key_persists_hashed_active_key(tmp_path):
    storage_path = tmp_path / "secrets" / "api_keys.json"
    service = ApiKeyService(str(storage_path))

    api_key = service.create_key("local-admin")

    assert api_key.startswith("lsa_")
    assert service.verify_api_key(api_key) is True
    assert service.verify_api_key("lsa_wrong") is False

    data = json.loads(storage_path.read_text(encoding="utf-8"))
    assert data["keys"][0]["name"] == "local-admin"
    assert data["keys"][0]["key_hash"].startswith("sha256$")
    assert api_key not in storage_path.read_text(encoding="utf-8")


def test_verify_api_key_ignores_inactive_keys(tmp_path):
    storage_path = tmp_path / "api_keys.json"
    service = ApiKeyService(str(storage_path))
    api_key = "lsa_inactive"

    storage_path.write_text(
        json.dumps(
            {
                "keys": [
                    {
                        "name": "disabled",
                        "key_hash": service.hash_api_key(api_key),
                        "is_active": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert service.verify_api_key(api_key) is False
