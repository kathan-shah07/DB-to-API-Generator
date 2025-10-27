import traceback
import uuid
import datetime
import storage


def format_exception_response(exc: Exception) -> tuple[int, dict, dict]:
    """Create structured response and log record for an exception.

    Returns (status_code, body_dict, log_record)
    """
    # timestamp
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if hasattr(exc, "status_code"):
        status_code = getattr(exc, "status_code")
        message = getattr(exc, "detail", str(exc))
        error_code = f"HTTP_{status_code}"
    else:
        status_code = 500
        message = str(exc) or exc.__class__.__name__
        error_code = "INTERNAL_ERROR"

    try:
        stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    except Exception:
        stack = "<no traceback available>"

    rid = uuid.uuid4().hex

    logrec = {
        "request_id": rid,
        "time": ts,
        "status": "error",
        "error_code": error_code,
        "message": message,
        "stack": stack,
    }

    # try to append log; ignore failures
    try:
        storage.append_log(logrec)
    except Exception:
        pass

    body = {"error_code": error_code, "message": message, "request_id": rid, "timestamp": ts}
    return status_code, body, logrec
