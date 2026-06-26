from django.db import models


class CodeSubmission(models.Model):
    title = models.CharField(max_length=200)
    programming_language = models.CharField(max_length=50)
    code_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class AIReview(models.Model):
    submission = models.ForeignKey(
        CodeSubmission,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    review_text = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Review for {self.submission.title}"