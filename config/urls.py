from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse
from django.db import connection
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """Simple health check - database ga bog'liq emas"""
    return HttpResponse("ok", content_type="text/plain")


def health_check_db(request):
    """Database health check"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok", "database": "connected"})
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JsonResponse({"status": "error", "database": str(e)}, status=503)


urlpatterns = [
    path('', health_check, name='root_health'),
    path('health/', health_check, name='health'),
    path('health/db/', health_check_db, name='health_db'),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
