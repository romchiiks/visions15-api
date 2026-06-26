from contextlib import suppress
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, status


class PerspectiveWarpService:
    OUTPUT_WIDTH = 2550
    OUTPUT_HEIGHT = 1680
    REQUIRED_IDS = (0, 1, 2, 3)
    REQUIRED_IDS_SET = set(REQUIRED_IDS)

    def warp_images(self, image_paths: Iterable[Path]) -> None:
        for image_path in image_paths:
            self.warp_image(image_path)

    def warp_image(self, image_path: Path) -> None:
        cv2, np = self._load_dependencies()

        temp_path = image_path.with_name(
            f".{image_path.stem}.warped{image_path.suffix}"
        )

        try:
            image = cv2.imread(str(image_path))
            if image is None:
                raise RuntimeError("failed to read image")

            detector = self._build_detector(cv2)
            corners, marker_ids = self._detect_markers(cv2, image, detector)
            source_points = self._build_source_points(np, corners, marker_ids)
            destination_points = np.array(
                [
                    [0, 0],
                    [self.OUTPUT_WIDTH - 1, 0],
                    [self.OUTPUT_WIDTH - 1, self.OUTPUT_HEIGHT - 1],
                    [0, self.OUTPUT_HEIGHT - 1],
                ],
                dtype=np.float32,
            )

            matrix = cv2.getPerspectiveTransform(
                source_points,
                destination_points,
            )
            warped = cv2.warpPerspective(
                image,
                matrix,
                (self.OUTPUT_WIDTH, self.OUTPUT_HEIGHT),
            )

            if not cv2.imwrite(str(temp_path), warped):
                raise RuntimeError("failed to write warped image")

            temp_path.replace(image_path)
        except HTTPException:
            raise
        except Exception as exc:
            with suppress(OSError):
                temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Perspective warp failed for image {image_path}: {exc}",
            ) from exc

    def _load_dependencies(self):
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Perspective warp requires opencv-contrib-python-headless "
                    "and numpy"
                ),
            ) from exc

        if not hasattr(cv2, "aruco"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Perspective warp requires OpenCV ArUco support",
            )

        return cv2, np

    def _build_detector(self, cv2):
        aruco_dictionary = cv2.aruco.getPredefinedDictionary(
            cv2.aruco.DICT_4X4_50
        )
        detector_parameters = cv2.aruco.DetectorParameters()

        if hasattr(cv2.aruco, "ArucoDetector"):
            return cv2.aruco.ArucoDetector(
                aruco_dictionary,
                detector_parameters,
            )

        return aruco_dictionary, detector_parameters

    def _detect_markers(self, cv2, image, detector):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if hasattr(detector, "detectMarkers"):
            corners, marker_ids, _ = detector.detectMarkers(gray)
        else:
            aruco_dictionary, detector_parameters = detector
            corners, marker_ids, _ = cv2.aruco.detectMarkers(
                gray,
                aruco_dictionary,
                parameters=detector_parameters,
            )

        if marker_ids is None:
            raise RuntimeError("required ArUco markers were not found")

        return corners, marker_ids.flatten()

    def _build_source_points(self, np, corners, marker_ids):
        marker_points = {
            int(marker_id): marker_corners[0]
            for marker_corners, marker_id in zip(corners, marker_ids)
        }

        missing_ids = self.REQUIRED_IDS_SET - marker_points.keys()
        if missing_ids:
            raise RuntimeError(
                f"required ArUco marker IDs were not found: {sorted(missing_ids)}"
            )

        return np.array(
            [
                marker_points[0][2],
                marker_points[1][3],
                marker_points[2][0],
                marker_points[3][1],
            ],
            dtype=np.float32,
        )
