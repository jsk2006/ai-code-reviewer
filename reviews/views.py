from django.shortcuts import get_object_or_404, redirect, render
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import CodeSubmissionForm
from .models import CodeSubmission
from .serializers import CodeSubmissionSerializer, ReviewRequestSerializer
from .services import generate_review


def home(request):
    if request.method == 'POST':
        form = CodeSubmissionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = CodeSubmissionForm()

    submissions = CodeSubmission.objects.all().order_by('-created_at')

    return render(request, 'reviews/home.html', {
        'form': form,
        'submissions': submissions,
    })


def submission_detail(request, id):
    submission = get_object_or_404(CodeSubmission, pk=id)

    return render(request, 'reviews/submission_detail.html', {
        'submission': submission,
    })


class CodeSubmissionListCreateAPIView(ListCreateAPIView):
    queryset = CodeSubmission.objects.all().order_by('-created_at')
    serializer_class = CodeSubmissionSerializer


class CodeSubmissionDetailAPIView(RetrieveAPIView):
    queryset = CodeSubmission.objects.all()
    serializer_class = CodeSubmissionSerializer

class CodeSubmissionUpdateAPIView(UpdateAPIView):
    queryset = CodeSubmission.objects.all()
    serializer_class = CodeSubmissionSerializer

class CodeSubmissionDeleteAPIView(DestroyAPIView):
    queryset = CodeSubmission.objects.all()
    serializer_class = CodeSubmissionSerializer


class ReviewAPIView(APIView):
    def post(self, request):

        serializer = ReviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = generate_review(
            title=serializer.validated_data["title"],
            programming_language=serializer.validated_data["programming_language"],
            code_content=serializer.validated_data["code_content"]
        )

        return Response(review.model_dump())