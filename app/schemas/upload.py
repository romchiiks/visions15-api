from pydantic import BaseModel


class UploadedProject(BaseModel):
    project_id: int
    project_name: str
    class_name: str
    imported_tasks_count: int


class UploadArchiveResponse(BaseModel):
    status: str
    projects: list[UploadedProject]
    saved_archive_path: str
    extracted_dir: str
    classes: list[str]
    imported_tasks_count: int
