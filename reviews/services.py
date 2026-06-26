import os

from dotenv import load_dotenv
from google import genai

from .models import CodeSubmission, AIReview

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def generate_review(title, programming_language, code_content):

    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=f"""
    You are an expert software engineer.

    Review the following {programming_language} code.

    Title: {title}

    Code:
    {code_content}

    Give constructive feedback in simple bullet points. Mehtion:
    1. Correctness
    2. Readability
    3. Efficiency
    4. Best practices
    5. Possible improvements
    """
    )

    review_text = response.text

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