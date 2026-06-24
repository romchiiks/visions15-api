import asyncio

from app.services.label_config_service import LabelConfigService
from app.services.project_service import ProjectService


class FakeLabelStudioClient:
    def __init__(self):
        self.calls = []
        self.import_calls = []

    async def create_project(self, title: str, label_config: str) -> dict:
        self.calls.append({"title": title, "label_config": label_config})
        return {"id": 12, "title": title}

    async def import_tasks(self, project_id: int, tasks: list[dict]) -> dict:
        self.import_calls.append({"project_id": project_id, "tasks": tasks})
        return {"task_count": len(tasks)}


def test_create_project_builds_label_config_and_maps_response():
    client = FakeLabelStudioClient()
    service = ProjectService(
        label_studio_client=client,
        label_config_service=LabelConfigService(),
    )

    result = asyncio.run(service.create_project("Demo dataset", ["cat", "dog"]))

    assert result == {
        "status": "success",
        "project_id": 12,
        "project_name": "Demo dataset",
        "classes": ["cat", "dog"],
    }
    assert client.calls[0]["title"] == "Demo dataset"
    assert '<Label value="cat"/>' in client.calls[0]["label_config"]
    assert '<Label value="dog"/>' in client.calls[0]["label_config"]


def test_create_project_from_metadata_with_tasks_imports_tasks():
    client = FakeLabelStudioClient()
    service = ProjectService(
        label_studio_client=client,
        label_config_service=LabelConfigService(),
    )
    metadata = {
        "dataset_update": {"name": "Demo dataset"},
        "classes": {"cat": {}, "dog": {}},
    }
    tasks = [
        {"data": {"image": "https://storage.test/datasets/cat.jpg"}},
        {"data": {"image": "https://storage.test/datasets/dog.jpg"}},
    ]

    result = asyncio.run(
        service.create_project_from_metadata_with_tasks(
            metadata=metadata,
            tasks=tasks,
        )
    )

    assert result["project_id"] == 12
    assert result["imported_tasks_count"] == 2
    assert client.import_calls == [{"project_id": 12, "tasks": tasks}]
