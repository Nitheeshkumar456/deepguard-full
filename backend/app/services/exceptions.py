"""
exceptions.py — Custom exception hierarchy for the AI inference pipeline.

Each exception class represents a distinct failure mode in the analysis
pipeline, enabling precise error handling and informative API responses.
None of these exceptions should cause the server to return fake or
fabricated analysis results — they always result in an explicit error state.
"""


class AIServiceError(Exception):
    """Base exception for all AI service errors."""

    def __init__(self, message: str = "An AI service error occurred."):
        self.message = message
        super().__init__(self.message)


class ModelUnavailableError(AIServiceError):
    """Raised when the model weights file is not found or fails to load."""

    def __init__(self, message: str = "AI model is not available or failed to load."):
        super().__init__(message)


class InvalidImageError(AIServiceError):
    """Raised when an image file cannot be decoded or opened by PIL."""

    def __init__(self, message: str = "The uploaded image could not be decoded."):
        super().__init__(message)


class CorruptFileError(AIServiceError):
    """Raised when file bytes are damaged, truncated, or otherwise unreadable."""

    def __init__(self, message: str = "The uploaded file appears to be corrupt or truncated."):
        super().__init__(message)


class InferenceError(AIServiceError):
    """Raised when the model forward pass fails unexpectedly."""

    def __init__(self, message: str = "Model inference failed during processing."):
        super().__init__(message)


class InferenceTimeoutError(AIServiceError):
    """Raised when inference exceeds the configured time limit."""

    def __init__(self, message: str = "Model inference timed out."):
        super().__init__(message)


class UnsupportedFormatError(AIServiceError):
    """Raised when the image format is not supported by the preprocessing pipeline."""

    def __init__(self, message: str = "The image format is not supported for analysis."):
        super().__init__(message)
