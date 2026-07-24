from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ReviewResult, Submission, SubmissionFile
from .validators import validate_submission_file


class SignupSerializer(serializers.ModelSerializer):
    """
    Registration serializer. Deliberately NOT a plain ModelSerializer over User's
    real fields — `password` needs write_only + hashing, and `email` should be
    required even though Django's default User model leaves it optional.
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def create(self, validated_data):
        # create_user() hashes the password; create() (the ModelSerializer default)
        # would save it in plain text, which is why we override this method.
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )


class SubmissionFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionFile
        fields = ['id', 'original_name', 'file', 'uploaded_at']
        read_only_fields = fields


class ReviewResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewResult
        fields = ['overall_score', 'summary', 'structured_review', 'created_at']
        read_only_fields = fields


class SubmissionSerializer(serializers.ModelSerializer):
    """
    Read-only representation used for the create response, the status/result
    endpoint (step 6), and the history list (step 7). `review` is null until the
    Celery task finishes and status flips to done/failed.
    """

    files = SubmissionFileSerializer(many=True, read_only=True)
    review = ReviewResultSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id', 'category', 'code_content', 'status', 'error_message',
            'files', 'review', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class SubmissionCreateSerializer(serializers.ModelSerializer):
    """
    Write-only serializer for POST /api/submissions/. Accepts multipart form data:
    `category` (required), `code_content` (optional raw pasted code), and zero or
    more `files` entries (repeat the `files` form key for each file — that's how
    HTML multipart forms and most HTTP clients send multiple files under one key).
    """

    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True,
        write_only=True,
    )

    class Meta:
        model = Submission
        fields = ['category', 'code_content', 'files']

    def validate_files(self, files):
        for uploaded_file in files:
            validate_submission_file(uploaded_file)
        return files

    def validate(self, attrs):
        code_content = attrs.get('code_content', '').strip()
        files = attrs.get('files', [])
        if not code_content and not files:
            raise serializers.ValidationError(
                'Provide code_content, at least one file, or both — an empty submission has nothing to review.'
            )
        return attrs

    def create(self, validated_data):
        files = validated_data.pop('files', [])
        submission = Submission.objects.create(
            user=self.context['request'].user,
            **validated_data,
        )
        for uploaded_file in files:
            SubmissionFile.objects.create(
                submission=submission,
                file=uploaded_file,
                original_name=uploaded_file.name,
            )
        return submission
