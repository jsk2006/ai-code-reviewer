from rest_framework import serializers

from .models import CodeSubmission


class CodeSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodeSubmission
        fields = ['id', 'title', 'programming_language', 'code_content', 'created_at']


class ReviewRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    programming_language = serializers.CharField(max_length=50)
    code_content = serializers.CharField()