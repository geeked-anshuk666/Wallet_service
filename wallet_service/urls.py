"""
urls.py — Root URL Configuration for the Wallet Service

Routes:
  /admin/              → Django admin panel
  /api/v1/...          → All wallet API endpoints (see wallets/urls.py)
  /health              → Liveness probe
  /schema              → Raw OpenAPI 3.0 JSON spec
  /docs                → Swagger UI (interactive API explorer)
  /redoc               → ReDoc (read-only API documentation)
"""

from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from wallets.views import HealthView

urlpatterns = [
    # ── Django Admin ──────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── API Routes (versioned under /api/v1/) ─────────────────
    path('api/v1/', include('wallets.urls')),

    # ── Health Check ──────────────────────────────────────────
    # Simple liveness probe — returns {"status": "healthy"}
    path('health', HealthView.as_view()),

    # ── API Documentation (powered by drf-spectacular) ────────
    path('schema', SpectacularAPIView.as_view(), name='schema'),               # Raw OpenAPI spec (JSON)
    path('docs', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),  # Swagger UI
    path('redoc', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),        # ReDoc
]
