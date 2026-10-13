"""Check the tensor contract of the MediaPipe hand model family."""

from math import prod
from struct import error as StructError


class HandLandmarkerSignature:
    def validate(self, data, name):
        # Import only during model validation, so settings data stays independent
        # of the inference runtime and model inspection happens on the loader thread.
        from mediapipe.tasks.metadata import schema_py_generated as schema

        try:
            model = schema.Model.GetRootAsModel(data, 0)
            if model.Version() != 3 or not model.SubgraphsLength():
                raise ValueError("Unsupported TensorFlow Lite model schema.")
            graph = model.Subgraphs(0)
            expected_outputs = 2 if name == "hand_detector.tflite" else 4
            if graph.InputsLength() != 1 or graph.OutputsLength() != expected_outputs:
                raise ValueError("The model's inputs and outputs do not match Hand Landmarker.")
            image = self._tensor_shape(graph, graph.Inputs(0), schema)
            if len(image) != 4 or image[0] != 1 or image[-1] != 3 or image[1] != image[2]:
                raise ValueError("Hand Landmarker requires a square RGB image input.")
            output_sizes = tuple(
                prod(self._tensor_shape(graph, graph.Outputs(index), schema))
                for index in range(expected_outputs)
            )
            expected_sizes = (2016 * 18, 2016) if expected_outputs == 2 else (63, 1, 1, 63)
            if output_sizes != expected_sizes:
                raise ValueError("The model must use MediaPipe's palm and 21-landmark output format.")
        except (IndexError, TypeError, OverflowError, StructError) as error:
            raise ValueError("The bundle contains an unreadable model signature.") from error

    @staticmethod
    def _tensor_shape(graph, index, schema):
        if not 0 <= index < graph.TensorsLength():
            raise ValueError("The model contains an invalid tensor reference.")
        tensor = graph.Tensors(index)
        if tensor.Type() != schema.TensorType.FLOAT32 or not 1 <= tensor.ShapeLength() <= 4:
            raise ValueError("Choose a Hand Landmarker model with floating-point image inputs and outputs.")
        shape = tuple(tensor.Shape(index) for index in range(tensor.ShapeLength()))
        if any(size <= 0 for size in shape):
            raise ValueError("Hand Landmarker requires fixed positive tensor dimensions.")
        return shape
