import httpx
from fastapi import HTTPException, status


class LabelStudioClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self.api_key}",
        }

    async def create_project(
        self,
        title: str,
        label_config: str,
    ) -> dict:
        url = f"{self.base_url}/api/projects"

        payload = {
            "title": title,
            "label_config": label_config,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30,
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Label Studio project creation failed",
                    "label_studio_status": response.status_code,
                    "label_studio_response": response.text,
                },
            )

        return response.json()