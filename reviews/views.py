from django.db import transaction
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Submission
from .serializers import SignupSerializer, SubmissionCreateSerializer, SubmissionSerializer
from .tasks import process_submission
from .throttles import SubmissionRateThrottle


class SignupView(CreateAPIView):
    """
    POST username/email/password -> creates a User. Doesn't return tokens itself;
    the client is expected to call /api/auth/login/ (TokenObtainPairView) right
    after, same as any "register then log in" flow. Keeping registration and
    login as separate endpoints (rather than auto-logging-in on signup) keeps
    each view doing one thing, and matches how simplejwt's views work.
    """

    serializer_class = SignupSerializer
    # Global DEFAULT_PERMISSION_CLASSES is IsAuthenticated (see settings/base.py) —
    # signup is the one endpoint that must be reachable by anonymous clients.
    permission_classes = [AllowAny]


class SubmissionListCreateAPIView(ListCreateAPIView):
    """
    POST  -> create a submission (Step 4): validates input, saves it with
             status="pending", and enqueues a Celery job. Returns 201 immediately
             — it does NOT wait for the LLM. That's the whole point of doing this
             asynchronously: the client gets an id to poll, not a slow response.
    GET   -> history (Step 7): paginated list of the current user's past
             submissions, most recent first (see Submission.Meta.ordering),
             each with its review nested once done.
    """

    def get_queryset(self):
        return Submission.objects.filter(user=self.request.user).prefetch_related('files', 'review')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SubmissionCreateSerializer
        return SubmissionSerializer

    def get_throttles(self):
        # Only throttle creation (Step 8) — browsing your own history (GET)
        # shouldn't burn the same per-day budget as kicking off LLM-costing reviews.
        if self.request.method == 'POST':
            return [SubmissionRateThrottle()]
        return []

    def perform_create(self, serializer):
        submission = serializer.save()
        # transaction.on_commit defers the .delay() call until after the DB
        # transaction actually commits. Without this, a Celery worker could pick
        # up the job and query for the Submission row before it's visible in the
        # database (a real race condition under load, not just theoretical).
        transaction.on_commit(lambda: process_submission.delay(submission.id))

    def create(self, request, *args, **kwargs):
        # Reuse DRF's default create() logic, but respond with SubmissionSerializer
        # (which includes id/status/files) instead of echoing back the input-only
        # SubmissionCreateSerializer fields.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        output_serializer = SubmissionSerializer(serializer.instance, context=self.get_serializer_context())
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class SubmissionDetailAPIView(RetrieveAPIView):
    """GET /api/submissions/<id>/ — the status/result endpoint (Step 6). Clients poll this."""

    serializer_class = SubmissionSerializer

    def get_queryset(self):
        # Scoping to request.user means requesting someone else's submission id
        # 404s instead of 403ing — we don't want to confirm the id even exists.
        return Submission.objects.filter(user=self.request.user).prefetch_related('files', 'review')
