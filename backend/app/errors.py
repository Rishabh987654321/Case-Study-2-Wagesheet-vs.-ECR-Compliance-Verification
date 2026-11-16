class AppError(Exception):
    """Base for API errors. Maps directly to the {"error","detail"} response shape."""

    error_code = "PROCESSING_ERROR"
    status_code = 500

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class InvalidFileError(AppError):
    error_code = "INVALID_FILE"
    status_code = 400


class FileTooLargeError(AppError):
    error_code = "FILE_TOO_LARGE"
    status_code = 400


class NotFoundError(AppError):
    error_code = "NOT_FOUND"
    status_code = 404


class ParseFailedError(AppError):
    error_code = "PARSE_FAILED"
    status_code = 422


class ProcessingError(AppError):
    error_code = "PROCESSING_ERROR"
    status_code = 500


class AlreadyProcessingError(AppError):
    error_code = "ALREADY_PROCESSING"
    status_code = 409
