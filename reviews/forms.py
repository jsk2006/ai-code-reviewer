from django import forms

from .models import CodeSubmission


class CodeSubmissionForm(forms.ModelForm):
    class Meta:
        model = CodeSubmission
        fields = ['title', 'programming_language', 'code_content']
