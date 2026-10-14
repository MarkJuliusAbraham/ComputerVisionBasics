"""Validate the bundle contract used by MediaPipe's HandLandmarker graph."""

from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from .model_signature import HandLandmarkerSignature


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = "tasks/hand_landmarker.task"


class HandLandmarkerAsset:
    family = "MediaPipe Hand Landmarker"
    model_files = ("hand_detector.tflite", "hand_landmarks_detector.tflite")

    def __init__(self, signature=None):
        self.signature = signature if signature is not None else HandLandmarkerSignature()

    def resolve(self, path):
        selected = Path(path).expanduser()
        return selected.resolve() if selected.is_absolute() else (PROJECT_ROOT / selected).resolve()

    def _resolve_bundle(self, path):
        selected = self.resolve(path)
        if selected.suffix.lower() != ".task":
            raise ValueError("Choose a MediaPipe Hand Landmarker .task bundle.")
        return selected

    def validate_path(self, path):
        """Perform inexpensive structural validation before accepting a selection."""
        selected = self._resolve_bundle(path)
        try:
            with ZipFile(selected) as bundle:
                self._validate_bundle(bundle)
        except (OSError, BadZipFile) as error:
            raise ValueError("The selected file is not a readable Hand Landmarker bundle.") from error
        return str(selected)

    def read(self, path):
        """Validate the exact bytes that the runtime will load, without extracting files."""
        selected = self._resolve_bundle(path)
        try:
            data = selected.read_bytes()
            with ZipFile(BytesIO(data)) as bundle:
                self._validate_bundle(bundle)
                for name in self.model_files:
                    self.signature.validate(bundle.read(name), name)
        except (OSError, BadZipFile) as error:
            raise ValueError("The selected file is missing or is not a readable model bundle.") from error
        return data

    def _validate_bundle(self, bundle):
        for name in self.model_files:
            try:
                with bundle.open(name) as model:
                    header = model.read(8)
            except (KeyError, RuntimeError, NotImplementedError, BadZipFile) as error:
                raise ValueError(
                    "This bundle is incompatible: it must contain both the hand detector "
                    "and hand landmark detector models."
                ) from error
            if header[4:8] != b"TFL3":
                raise ValueError("The bundle contains an invalid TensorFlow Lite model.")
