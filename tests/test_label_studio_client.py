from app.clients.label_studio_client import LabelStudioClient


def test_label_studio_client_uses_legacy_token_auth_by_default():
    client = LabelStudioClient(
        base_url="http://label-studio.test",
        api_key="legacy-token",
    )

    assert client.headers["Authorization"] == "Token legacy-token"


def test_label_studio_client_can_use_bearer_auth():
    client = LabelStudioClient(
        base_url="http://label-studio.test",
        api_key="pat-token",
        auth_scheme="Bearer",
    )

    assert client.headers["Authorization"] == "Bearer pat-token"
