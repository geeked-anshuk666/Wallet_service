"""
audit.py — Resilient Audit Log Writer

Provides a single function (write_audit_log) that records every API request
into the AuditLog table. Key design principle: this function NEVER raises.
If the audit write fails (disk full, DB down, etc.), the error is logged
to stderr and the caller's response is completely unaffected.

Audit writes happen OUTSIDE the main database transaction in services.py,
so even rolled-back operations (e.g., a failed spend) still produce a log entry.
"""

import logging

from .models import AuditLog

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """
    Extract the real client IP from the request.
    Checks X-Forwarded-For first (for requests behind a reverse proxy like Render),
    then falls back to REMOTE_ADDR for direct connections.
    """
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs — the first one is the real client
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def write_audit_log(
    action: str,
    status: str,
    response_status: int,
    request=None,
    wallet_id=None,
    request_body=None,
    error_message=None,
):
    """
    Write one audit log entry. Never raises — a write failure is logged
    server-side but the caller's response is never affected.

    This is intentionally a fire-and-forget operation. We don't want a flaky
    audit write to cause a 500 on a legitimate user request.
    """
    try:
        AuditLog.objects.create(
            action=action,
            wallet_id=wallet_id,
            status=status,
            request_body=request_body,
            response_status=response_status,
            ip_address=get_client_ip(request) if request else None,
            error_message=error_message,
        )
    except Exception as e:
        # Log to stderr so ops can still see audit failures in container logs,
        # but never let this bubble up and break a client request
        logger.error(f"audit log write failed: {e}", exc_info=True)
