import logging
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


def generate_request_id() -> str:
    return uuid.uuid4().hex[:12]


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get() or "-"
        record.user_id = user_id_var.get() or "-"
        return True
