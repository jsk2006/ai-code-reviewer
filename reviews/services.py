import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .schemas import ReviewSchema
from .models import CodeSubmission, AIReview

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def generate_review(title, programming_language, code_content):
    try:
        prompt=f"""
        You are an expert and experienced software engineer.

        Review the following {programming_language} code and give constructive feedback.
        The code can be a competetive coding problem solution or a industry/ production level code or a personal project code etc.
        Examine and figure out what the code is trying to acheive and analyze according to that.
        Don't give sugar coated feedback, be honest and straightforward.

        Title: {title}

        Code:
        {code_content}

        Give constructive feedback in simple bullet points. Mention:
        1. Correctness- logic errors, edge cases, etc.
        2. Readability- code readability, comments, etc.
        3. Efficiency- time complexity, space complexity, memory usage, etc.
        4. Best practices- coding conventions, best practices, etc.
        5. Possible improvements- state properly what the issue is and how to improve it.
        6. If it is a personal project then how to improve/ what all features to add for beginner, intermediate or advanced level.
        7. If it is industry/ production level code- then focus on scalability if applicable on the code and what all best practices to follow.
        8. If it is a competetive coding problem solution- then focus on the logic- bruteforce and optimized solutions, time and space complexity, etc.
        9. Overall- give a overall score and feedback on the code.

                """
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReviewSchema,
            ),
        )

        review = ReviewSchema.model_validate_json(response.text)
        review_text = review.summary
    except Exception as e:
        print(e)
        raise RuntimeError("Failed to generate AI review") from e

    submission = CodeSubmission.objects.create(
        title=title,
        programming_language=programming_language,
        code_content=code_content
    )

    AIReview.objects.create(
        submission=submission,
        overall_score=review.overall_score,
        summary=review.summary,
        structured_review=review.model_dump()
    )

    return review 

