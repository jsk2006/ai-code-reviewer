"""
URL configuration for ai_code_reviewer project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reviews.urls')),
]

# Serve uploaded files (SubmissionFile.file) in development. In production this
# would be handled by nginx/S3/etc. instead of Django — DEBUG gates it here.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
