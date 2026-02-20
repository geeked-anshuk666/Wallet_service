import json
import logging

from django.core.paginator import Paginator
from django_ratelimit.core import is_ratelimited
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import write_audit_log
from .exceptions import InsufficientBalanceError, WalletNotFoundError
from .models import AuditLog, LedgerEntry, Wallet
from .services import bonus, spend, topup

logger = logging.getLogger(__name__)


class TopupView(APIView):
    def post(self, request, wallet_id):
        limited = is_ratelimited(request, group='topup', key='ip', rate='60/m', increment=True)
        if limited:
            write_audit_log(
                action=AuditLog.TOPUP, status=AuditLog.FAILED,
                response_status=429, request=request,
                wallet_id=str(wallet_id), error_message='rate limit exceeded',
            )
            return Response(
                {'error': 'RATE_LIMIT_EXCEEDED', 'message': 'too many requests, slow down'},
                status=429,
            )

        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            write_audit_log(
                action=AuditLog.TOPUP, status=AuditLog.FAILED,
                response_status=400, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='Idempotency-Key header is required',
            )
            return Response({'error': 'Idempotency-Key header is required'}, status=400)

        amount = request.data.get('amount')
        asset_type_id = request.data.get('asset_type_id')
        if not amount or not asset_type_id:
            write_audit_log(
                action=AuditLog.TOPUP, status=AuditLog.FAILED,
                response_status=400, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='amount and asset_type_id are required',
            )
            return Response({'error': 'amount and asset_type_id are required'}, status=400)

        if not isinstance(amount, int) or amount <= 0:
            write_audit_log(
                action=AuditLog.TOPUP, status=AuditLog.FAILED,
                response_status=400, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='amount must be a positive integer',
            )
            return Response({'error': 'amount must be a positive integer'}, status=400)

        try:
            result = topup(str(wallet_id), amount, asset_type_id, idempotency_key)
            response_status = 200 if result.get('replayed') else 201
        except WalletNotFoundError as e:
            write_audit_log(
                action=AuditLog.TOPUP, status=AuditLog.FAILED,
                response_status=422, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message=str(e),
            )
            return Response({'error': 'WALLET_NOT_FOUND', 'message': str(e)}, status=422)
        except Exception as e:
            logger.error(f"topup error: {e}", exc_info=True)
            write_audit_log(
                action=AuditLog.TOPUP, status=AuditLog.FAILED,
                response_status=500, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='internal server error',
            )
            return Response({'error': 'INTERNAL_ERROR'}, status=500)

        write_audit_log(
            action=AuditLog.TOPUP, status=AuditLog.SUCCESS,
            response_status=response_status, request=request,
            wallet_id=str(wallet_id), request_body=request.data,
        )
        return Response(result, status=response_status)


class BonusView(APIView):
    def post(self, request, wallet_id):
        limited = is_ratelimited(request, group='bonus', key='ip', rate='60/m', increment=True)
        if limited:
            write_audit_log(
                action=AuditLog.BONUS, status=AuditLog.FAILED,
                response_status=429, request=request,
                wallet_id=str(wallet_id), error_message='rate limit exceeded',
            )
            return Response(
                {'error': 'RATE_LIMIT_EXCEEDED', 'message': 'too many requests, slow down'},
                status=429,
            )

        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            write_audit_log(
                action=AuditLog.BONUS, status=AuditLog.FAILED,
                response_status=400, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='Idempotency-Key header is required',
            )
            return Response({'error': 'Idempotency-Key header is required'}, status=400)

        amount = request.data.get('amount')
        asset_type_id = request.data.get('asset_type_id')
        if not amount or not asset_type_id:
            write_audit_log(
                action=AuditLog.BONUS, status=AuditLog.FAILED,
                response_status=400, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='amount and asset_type_id are required',
            )
            return Response({'error': 'amount and asset_type_id are required'}, status=400)

        if not isinstance(amount, int) or amount <= 0:
            write_audit_log(
                action=AuditLog.BONUS, status=AuditLog.FAILED,
                response_status=400, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='amount must be a positive integer',
            )
            return Response({'error': 'amount must be a positive integer'}, status=400)

        try:
            result = bonus(str(wallet_id), amount, asset_type_id, idempotency_key)
            response_status = 200 if result.get('replayed') else 201
        except WalletNotFoundError as e:
            write_audit_log(
                action=AuditLog.BONUS, status=AuditLog.FAILED,
                response_status=422, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message=str(e),
            )
            return Response({'error': 'WALLET_NOT_FOUND', 'message': str(e)}, status=422)
        except Exception as e:
            logger.error(f"bonus error: {e}", exc_info=True)
            write_audit_log(
                action=AuditLog.BONUS, status=AuditLog.FAILED,
                response_status=500, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='internal server error',
            )
            return Response({'error': 'INTERNAL_ERROR'}, status=500)

        write_audit_log(
            action=AuditLog.BONUS, status=AuditLog.SUCCESS,
            response_status=response_status, request=request,
            wallet_id=str(wallet_id), request_body=request.data,
        )
        return Response(result, status=response_status)


class SpendView(APIView):
    def post(self, request, wallet_id):
        limited = is_ratelimited(request, group='spend', key='ip', rate='60/m', increment=True)
        if limited:
            write_audit_log(
                action=AuditLog.SPEND, status=AuditLog.FAILED,
                response_status=429, request=request,
                wallet_id=str(wallet_id), error_message='rate limit exceeded',
            )
            return Response(
                {'error': 'RATE_LIMIT_EXCEEDED', 'message': 'too many requests, slow down'},
                status=429,
            )

        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            write_audit_log(
                action=AuditLog.SPEND, status=AuditLog.FAILED,
                response_status=400, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='Idempotency-Key header is required',
            )
            return Response({'error': 'Idempotency-Key header is required'}, status=400)

        amount = request.data.get('amount')
        asset_type_id = request.data.get('asset_type_id')
        if not amount or not asset_type_id:
            write_audit_log(
                action=AuditLog.SPEND, status=AuditLog.FAILED,
                response_status=400, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='amount and asset_type_id are required',
            )
            return Response({'error': 'amount and asset_type_id are required'}, status=400)

        if not isinstance(amount, int) or amount <= 0:
            write_audit_log(
                action=AuditLog.SPEND, status=AuditLog.FAILED,
                response_status=400, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='amount must be a positive integer',
            )
            return Response({'error': 'amount must be a positive integer'}, status=400)

        try:
            result = spend(str(wallet_id), amount, asset_type_id, idempotency_key)
            response_status = 200 if result.get('replayed') else 201
        except InsufficientBalanceError as e:
            write_audit_log(
                action=AuditLog.SPEND, status=AuditLog.FAILED,
                response_status=422, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message=str(e),
            )
            return Response({'error': 'INSUFFICIENT_BALANCE', 'message': str(e)}, status=422)
        except WalletNotFoundError as e:
            write_audit_log(
                action=AuditLog.SPEND, status=AuditLog.FAILED,
                response_status=422, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message=str(e),
            )
            return Response({'error': 'WALLET_NOT_FOUND', 'message': str(e)}, status=422)
        except Exception as e:
            logger.error(f"spend error: {e}", exc_info=True)
            write_audit_log(
                action=AuditLog.SPEND, status=AuditLog.FAILED,
                response_status=500, request=request,
                wallet_id=str(wallet_id), request_body=request.data,
                error_message='internal server error',
            )
            return Response({'error': 'INTERNAL_ERROR'}, status=500)

        write_audit_log(
            action=AuditLog.SPEND, status=AuditLog.SUCCESS,
            response_status=response_status, request=request,
            wallet_id=str(wallet_id), request_body=request.data,
        )
        return Response(result, status=response_status)


class BalanceView(APIView):
    def get(self, request, wallet_id):
        limited = is_ratelimited(request, group='balance', key='ip', rate='200/m', increment=True)
        if limited:
            write_audit_log(
                action=AuditLog.BALANCE_READ, status=AuditLog.FAILED,
                response_status=429, request=request,
                wallet_id=str(wallet_id), error_message='rate limit exceeded',
            )
            return Response(
                {'error': 'RATE_LIMIT_EXCEEDED', 'message': 'too many requests, slow down'},
                status=429,
            )

        try:
            wallet = Wallet.objects.select_related('asset_type', 'user').get(id=wallet_id)
        except Wallet.DoesNotExist:
            write_audit_log(
                action=AuditLog.BALANCE_READ, status=AuditLog.FAILED,
                response_status=404, request=request,
                wallet_id=str(wallet_id),
                error_message=f'wallet {wallet_id} not found',
            )
            return Response({'error': 'wallet not found'}, status=404)

        result = {
            'wallet_id': str(wallet.id),
            'user': wallet.user.username,
            'asset_type': wallet.asset_type.name,
            'symbol': wallet.asset_type.symbol,
            'balance': wallet.balance,
        }

        write_audit_log(
            action=AuditLog.BALANCE_READ, status=AuditLog.SUCCESS,
            response_status=200, request=request,
            wallet_id=str(wallet_id),
        )
        return Response(result, status=200)


class TransactionHistoryView(APIView):
    def get(self, request, wallet_id):
        limited = is_ratelimited(request, group='transactions', key='ip', rate='200/m', increment=True)
        if limited:
            write_audit_log(
                action=AuditLog.TRANSACTION_HISTORY, status=AuditLog.FAILED,
                response_status=429, request=request,
                wallet_id=str(wallet_id), error_message='rate limit exceeded',
            )
            return Response(
                {'error': 'RATE_LIMIT_EXCEEDED', 'message': 'too many requests, slow down'},
                status=429,
            )

        try:
            wallet = Wallet.objects.get(id=wallet_id)
        except Wallet.DoesNotExist:
            write_audit_log(
                action=AuditLog.TRANSACTION_HISTORY, status=AuditLog.FAILED,
                response_status=404, request=request,
                wallet_id=str(wallet_id),
                error_message=f'wallet {wallet_id} not found',
            )
            return Response({'error': 'wallet not found'}, status=404)

        entries = LedgerEntry.objects.filter(
            wallet=wallet,
        ).select_related('transaction', 'asset_type').order_by('-created_at')

        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 20)
        try:
            page = int(page)
            per_page = min(int(per_page), 100)
        except (ValueError, TypeError):
            page = 1
            per_page = 20

        paginator = Paginator(entries, per_page)
        page_obj = paginator.get_page(page)

        results = [
            {
                'transaction_id': str(entry.transaction.id),
                'type': entry.transaction.type,
                'direction': entry.direction,
                'amount': entry.amount,
                'asset_type': entry.asset_type.name,
                'created_at': entry.created_at.isoformat(),
            }
            for entry in page_obj
        ]

        write_audit_log(
            action=AuditLog.TRANSACTION_HISTORY, status=AuditLog.SUCCESS,
            response_status=200, request=request,
            wallet_id=str(wallet_id),
        )
        return Response({
            'wallet_id': str(wallet_id),
            'transactions': results,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
        }, status=200)


class HealthView(APIView):
    def get(self, request):
        write_audit_log(
            action=AuditLog.HEALTH_CHECK, status=AuditLog.SUCCESS,
            response_status=200, request=request,
        )
        return Response({'status': 'healthy'}, status=200)
