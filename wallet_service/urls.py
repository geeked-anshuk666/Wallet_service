from django.contrib import admin
from django.urls import path, include

from wallets.views import HealthView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('wallets.urls')),
    path('health', HealthView.as_view()),
]
