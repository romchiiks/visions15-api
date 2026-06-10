from pydantic import BaseModel, Field, field_validator


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)
    classes: list[str] = Field(min_length=1)

    @field_validator("classes")
    @classmethod
    def validate_classes(cls, classes: list[str]) -> list[str]:
        for class_name in classes:
            if not class_name.strip():
                raise ValueError("classes must not contain empty values")
        return classes


class CreateProjectResponse(BaseModel):
    status: str
    project_id: int
    project_name: str
    classes: list[str]
