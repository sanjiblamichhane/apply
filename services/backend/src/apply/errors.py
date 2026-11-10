"""
What can go wrong, as stable codes, and the exceptions that carry them.

Code anywhere raises one of the kinds at the bottom (``NotFound(ErrorCode.PROFILE_NOT_FOUND)``). The API turns it
into an RFC 9457 problem document (apply/api/problems.py). People never see ``detail``: the apps show their own
translated sentence for the ``code``, so ``detail`` is a note for logs and developers.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # General
    INTERNAL = "INTERNAL"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    DATABASE_NOT_READY = "DATABASE_NOT_READY"
    # Accounts and sessions
    UNAUTHENTICATED = "UNAUTHENTICATED"
    SIGN_IN_FAILED = "SIGN_IN_FAILED"
    SIGN_IN_LOCKED = "SIGN_IN_LOCKED"
    ORIGIN_NOT_ALLOWED = "ORIGIN_NOT_ALLOWED"
    OWNER_EXISTS = "OWNER_EXISTS"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    EMAIL_TAKEN = "EMAIL_TAKEN"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    OWNER_ONLY = "OWNER_ONLY"
    ACCOUNT_IS_OWNER = "ACCOUNT_IS_OWNER"
    PASSWORD_TOO_SHORT = "PASSWORD_TOO_SHORT"
    RESET_LINK_INVALID = "RESET_LINK_INVALID"
    MAIL_NOT_SET_UP = "MAIL_NOT_SET_UP"
    # Personal API tokens
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_NOT_ALLOWED = "TOKEN_NOT_ALLOWED"
    TOKEN_SCOPE_MISSING = "TOKEN_SCOPE_MISSING"
    TOKEN_NOT_FOUND = "TOKEN_NOT_FOUND"
    # Packs
    PACK_NOT_FOUND = "PACK_NOT_FOUND"
    DOCUMENT_TYPE_NOT_FOUND = "DOCUMENT_TYPE_NOT_FOUND"
    DOCUMENT_TYPE_NOT_GENERATABLE = "DOCUMENT_TYPE_NOT_GENERATABLE"
    INVALID_ATTRIBUTES = "INVALID_ATTRIBUTES"
    # Profiles
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    PROFILE_REQUIRED = "PROFILE_REQUIRED"
    PROFILE_PACK_MISMATCH = "PROFILE_PACK_MISMATCH"
    PROFILE_NOT_READ = "PROFILE_NOT_READ"
    # Uploading a file (a resume, to make a profile)
    UPLOAD_TOO_LARGE = "UPLOAD_TOO_LARGE"
    UPLOAD_UNSUPPORTED = "UPLOAD_UNSUPPORTED"
    UPLOAD_NO_TEXT = "UPLOAD_NO_TEXT"
    # Document templates (uploaded HTML)
    TEMPLATE_PROBLEMS = "TEMPLATE_PROBLEMS"
    # Files (the bucket)
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
    # Opportunities and extraction
    OPPORTUNITY_NOT_FOUND = "OPPORTUNITY_NOT_FOUND"
    URL_OR_TEXT_REQUIRED = "URL_OR_TEXT_REQUIRED"
    URL_NOT_ALLOWED = "URL_NOT_ALLOWED"
    ADDRESS_NOT_ALLOWED = "ADDRESS_NOT_ALLOWED"
    FETCH_FAILED = "FETCH_FAILED"
    FETCH_BLOCKED = "FETCH_BLOCKED"
    FETCH_NOT_HTML = "FETCH_NOT_HTML"
    FETCH_TOO_LARGE = "FETCH_TOO_LARGE"
    FETCH_TOO_LITTLE_TEXT = "FETCH_TOO_LITTLE_TEXT"
    FETCH_TOO_MANY_REDIRECTS = "FETCH_TOO_MANY_REDIRECTS"
    EXTRACT_FAILED = "EXTRACT_FAILED"
    # Applications and pipeline
    APPLICATION_NOT_FOUND = "APPLICATION_NOT_FOUND"
    APPLICATION_EXISTS = "APPLICATION_EXISTS"
    STAGE_NOT_FOUND = "STAGE_NOT_FOUND"
    # Documents
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    # Discovery
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    SOURCE_KIND_NOT_FOUND = "SOURCE_KIND_NOT_FOUND"
    SOURCE_TOO_SOON = "SOURCE_TOO_SOON"
    SOURCE_NOT_RECOGNISED = "SOURCE_NOT_RECOGNISED"
    SOURCE_FAILED = "SOURCE_FAILED"
    SEARCH_NOT_FOUND = "SEARCH_NOT_FOUND"
    MATCH_NOT_FOUND = "MATCH_NOT_FOUND"
    SCORE_CAP_REACHED = "SCORE_CAP_REACHED"
    # Review and applying
    DOCUMENT_NOT_READY = "DOCUMENT_NOT_READY"
    WARNING_NOT_FOUND = "WARNING_NOT_FOUND"
    NOTHING_TO_REWRITE = "NOTHING_TO_REWRITE"
    RENDER_PENDING = "RENDER_PENDING"
    ANSWER_NOT_FOUND = "ANSWER_NOT_FOUND"
    ANSWER_EXISTS = "ANSWER_EXISTS"
    SUBMISSION_NOT_FOUND = "SUBMISSION_NOT_FOUND"
    UNDO_TOO_LATE = "UNDO_TOO_LATE"
    # Auto: the runs themselves
    AUTO_RUN_NOT_FOUND = "AUTO_RUN_NOT_FOUND"
    AUTO_ACTION_NOT_ALLOWED = "AUTO_ACTION_NOT_ALLOWED"
    RUNNER_TASK_NOT_FOUND = "RUNNER_TASK_NOT_FOUND"
    # Auto: why a run needs you (logic/auto.py)
    AUTO_PAUSED = "AUTO_PAUSED"
    AUTO_CAP_REACHED = "AUTO_CAP_REACHED"
    AUTO_SAME_ISSUER = "AUTO_SAME_ISSUER"
    AUTO_CLOSED = "AUTO_CLOSED"
    AUTO_UNSUPPORTED_BOARD = "AUTO_UNSUPPORTED_BOARD"
    AUTO_PROFILE_REQUIRED = "AUTO_PROFILE_REQUIRED"
    AUTO_DOCUMENT_FAILED = "AUTO_DOCUMENT_FAILED"
    AUTO_CLAIMS_UNCHECKED = "AUTO_CLAIMS_UNCHECKED"
    AUTO_CLAIM_WARNINGS = "AUTO_CLAIM_WARNINGS"
    AUTO_TIMED_OUT = "AUTO_TIMED_OUT"
    AUTO_CAPTCHA = "AUTO_CAPTCHA"
    AUTO_SIGN_IN = "AUTO_SIGN_IN"
    AUTO_FORM_MISSING = "AUTO_FORM_MISSING"
    AUTO_CONSENT_REQUIRED = "AUTO_CONSENT_REQUIRED"
    AUTO_REQUIRED_UNANSWERED = "AUTO_REQUIRED_UNANSWERED"
    AUTO_DRAFT_UNSUPPORTED = "AUTO_DRAFT_UNSUPPORTED"
    AUTO_DOCUMENTS_CHANGED = "AUTO_DOCUMENTS_CHANGED"
    AUTO_FORM_CHANGED = "AUTO_FORM_CHANGED"
    AUTO_VALIDATION_ERROR = "AUTO_VALIDATION_ERROR"
    AUTO_NO_CONFIRMATION = "AUTO_NO_CONFIRMATION"
    AUTO_SEND_UNKNOWN = "AUTO_SEND_UNKNOWN"
    AUTO_RUNNER_FAILED = "AUTO_RUNNER_FAILED"
    # The model
    LLM_UNREACHABLE = "LLM_UNREACHABLE"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_BAD_REPLY = "LLM_BAD_REPLY"
    LLM_EMPTY_REPLY = "LLM_EMPTY_REPLY"
    LLM_MODEL_MISSING = "LLM_MODEL_MISSING"
    # Choosing the model (Settings → Model)
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_TEST_FAILED = "MODEL_TEST_FAILED"


@dataclass(frozen=True)
class Kind:
    """The HTTP side of a failure: its status, a short label, and the code used when none is given."""

    status: int
    label: str
    fallback: ErrorCode

    @property
    def uri(self) -> str:
        return "urn:apply:error:" + self.label.lower().replace(" ", "-")


class ApplyError(Exception):
    kind = Kind(500, "Internal", ErrorCode.INTERNAL)

    def __init__(
        self,
        code: ErrorCode | None = None,
        detail: str | None = None,
        *,
        extra: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.code = code if code is not None else self.kind.fallback
        self.detail = detail if detail is not None else self.kind.label
        self.extra = dict(extra or {})
        self.headers = dict(headers or {})
        super().__init__(f"{self.code}: {self.detail}")

    @property
    def status(self) -> int:
        return self.kind.status

    def as_problem(self, **override: Any) -> dict[str, Any]:
        """The RFC 9457 body: the standard members, then ``code``, then anything extra (``errors``, limits)."""
        body = {"type": self.kind.uri, "title": self.kind.label, "status": self.status, "detail": self.detail}
        return body | {"code": self.code.value} | self.extra | override


class InvalidArgument(ApplyError):
    kind = Kind(422, "Invalid argument", ErrorCode.VALIDATION_FAILED)


class Unauthenticated(ApplyError):
    kind = Kind(401, "Unauthenticated", ErrorCode.UNAUTHENTICATED)


class PermissionDenied(ApplyError):
    kind = Kind(403, "Permission denied", ErrorCode.ORIGIN_NOT_ALLOWED)


class NotFound(ApplyError):
    kind = Kind(404, "Not found", ErrorCode.NOT_FOUND)


class Conflict(ApplyError):
    kind = Kind(409, "Conflict", ErrorCode.APPLICATION_EXISTS)


class TooManyRequests(ApplyError):
    kind = Kind(429, "Too many requests", ErrorCode.TOO_MANY_REQUESTS)


class Unavailable(ApplyError):
    kind = Kind(503, "Unavailable", ErrorCode.DATABASE_NOT_READY)


class MethodNotAllowed(ApplyError):
    kind = Kind(405, "Method not allowed", ErrorCode.METHOD_NOT_ALLOWED)
