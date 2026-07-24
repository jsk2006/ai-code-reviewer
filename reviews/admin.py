from django.contrib import admin

from .models import ReviewResult, Submission, SubmissionFile


class SubmissionFileInline(admin.TabularInline):
    model = SubmissionFile
    extra = 0


class ReviewResultInline(admin.StackedInline):
    model = ReviewResult
    extra = 0


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'category', 'status', 'created_at']
    list_filter = ['category', 'status']
    inlines = [SubmissionFileInline, ReviewResultInline]
