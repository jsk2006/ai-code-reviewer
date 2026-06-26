from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('submission/<int:id>/', views.submission_detail, name='submission_detail'),
    path('api/submissions/', views.CodeSubmissionListCreateAPIView.as_view(), name='api_submission_list'),
    path('api/submissions/<int:pk>/', views.CodeSubmissionDetailAPIView.as_view(), name='api_submission_detail'),
    path('api/review/', views.ReviewAPIView.as_view(), name='api_review'),
]
