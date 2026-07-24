from rest_framework.throttling import UserRateThrottle


class SubmissionRateThrottle(UserRateThrottle):
    """
    Limits how many submissions a single user can *create* per day (rate comes
    from DEFAULT_THROTTLE_RATES["submission"] in settings/base.py, itself read
    from the SUBMISSION_THROTTLE_RATE env var). Deliberately its own throttle
    scope rather than a blanket per-user API throttle, so polling GET
    /api/submissions/<id>/ for status doesn't eat into the same budget as
    creating new (LLM-costing) submissions.
    """

    scope = 'submission'
