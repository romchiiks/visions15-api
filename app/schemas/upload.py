from pydantic import BaseModel


class UploadArchiveResponse(BaseModel):
    status: str
    project_id: int
    project_name: str
    saved_archive_path: str
    extracted_dir: str
    classes: list[str]