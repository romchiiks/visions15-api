import pytest
from pydantic import ValidationError

from app.schemas.project import CreateProjectRequest


def test_create_project_request_trims_values():
    data = CreateProjectRequest(
        project_name=" Demo dataset ",
        classes=[" cat ", "dog"],
    )

    assert data.project_name == "Demo dataset"
    assert data.classes == ["cat", "dog"]


def test_create_project_request_rejects_blank_class_name():
    with pytest.raises(ValidationError):
        CreateProjectRequest(
            project_name="Demo dataset",
            classes=["cat", "   "],
        )
