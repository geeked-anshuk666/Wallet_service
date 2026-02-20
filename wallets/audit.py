import logging

from .models import AuditLog

logger = logging.getLogger(__name__)


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
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
        logger.error(f"audit log write failed: {e}", exc_info=True)
