from django.contrib import admin

from .models import CodeSubmission, AIReview


admin.site.register(CodeSubmission)
admin.site.register(AIReview)
