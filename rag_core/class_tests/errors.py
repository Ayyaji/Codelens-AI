"""Errors the class-test routes turn into HTTP responses."""


class ClassTestError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)
