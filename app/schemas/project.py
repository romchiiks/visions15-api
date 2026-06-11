from pydantic import BaseModel, Field, field_validator


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)
    classes: list[str] = Field(min_length=1)

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, project_name: str) -> str:
        project_name = project_name.strip()
        if not project_name:
            raise ValueError("project_name must be a non-empty string")
        return project_name

    @field_validator("classes")
    @classmethod
    def validate_classes(cls, classes: list[str]) -> list[str]:
        normalized_classes = []

        for class_name in classes:
            class_name = class_name.strip()
            if not class_name:
                raise ValueError("classes must not contain empty values")
            normalized_classes.append(class_name)

        return normalized_classes


class CreateProjectResponse(BaseModel):
    status: str
    project_id: int
    project_name: str
    classes: list[str]
