from .models import CodeSubmission, AIReview


def generate_review(title, programming_language, code_content):

    review_text = (
        "Good code. Consider adding comments "
        "and handling edge cases."
    )

    submission = CodeSubmission.objects.create(
        title=title,
        programming_language=programming_language,
        code_content=code_content
    )

    AIReview.objects.create(
        submission=submission,
        review_text=review_text
    )

    return review_text