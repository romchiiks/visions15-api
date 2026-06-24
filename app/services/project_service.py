from app.clients.label_studio_client import LabelStudioClient
from app.services.label_config_service import LabelConfigService


class ProjectService:
    def __init__(
        self,
        label_studio_client: LabelStudioClient,
        label_config_service: LabelConfigService,
    ):
        self.label_studio_client = label_studio_client
        self.label_config_service = label_config_service

    async def create_project(
        self,
        project_name: str,
        classes: list[str],
    ):
        label_config = self.label_config_service.build_object_detection_config(
            classes=classes
        )

        project = await self.label_studio_client.create_project(
            title=project_name,
            label_config=label_config,
        )

        return {
            "status": "success",
            "project_id": project["id"],
            "project_name": project["title"],
            "classes": classes,
        }

    async def create_project_from_metadata(
        self,
        metadata: dict,
    ):
        project_name = metadata["dataset_update"]["name"]
        classes = list(metadata["classes"].keys())

        return await self.create_project(
            project_name=project_name,
            classes=classes,
        )

    async def create_project_from_metadata_with_tasks(
        self,
        metadata: dict,
        tasks: list[dict],
    ):
        project = await self.create_project_from_metadata(metadata=metadata)
        import_result = {}

        if tasks:
            import_result = await self.label_studio_client.import_tasks(
                project_id=project["project_id"],
                tasks=tasks,
            )

        project["imported_tasks_count"] = import_result.get("task_count", len(tasks))
        project["task_import"] = import_result

        return project

    async def create_projects_from_metadata_with_tasks_by_class(
        self,
        metadata: dict,
        tasks_by_class: dict[str, list[dict]],
    ):
        dataset_name = metadata["dataset_update"]["name"]
        projects = []

        for class_name in metadata["classes"].keys():
            project = await self.create_project(
                project_name=f"{class_name}-{dataset_name}",
                classes=[class_name],
            )
            tasks = tasks_by_class.get(class_name, [])
            import_result = {}

            if tasks:
                import_result = await self.label_studio_client.import_tasks(
                    project_id=project["project_id"],
                    tasks=tasks,
                )

            project["class_name"] = class_name
            project["imported_tasks_count"] = import_result.get(
                "task_count",
                len(tasks),
            )
            project["task_import"] = import_result
            projects.append(project)

        return projects
