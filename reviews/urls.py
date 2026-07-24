from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path('api/auth/signup/', views.SignupView.as_view(), name='api_signup'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='api_login'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='api_refresh'),

    # POST creates a submission (Step 4) + enqueues review; GET lists your
    # submission history, paginated (Step 7).
    path('api/submissions/', views.SubmissionListCreateAPIView.as_view(), name='api_submission_list_create'),
    # GET polls status and, once done, the review result (Step 6).
    path('api/submissions/<int:pk>/', views.SubmissionDetailAPIView.as_view(), name='api_submission_detail'),
]
