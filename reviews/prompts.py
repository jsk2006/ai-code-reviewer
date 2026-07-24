from .models import Submission

# Per-category instructions injected into the shared prompt template below. This
# is the mechanism the spec asks for: same LLM, same output schema, but the
# *questions we ask it* change based on how the user tagged their submission.
CATEGORY_INSTRUCTIONS = {
    Submission.Category.DSA: """
This is a DSA / competitive programming submission. Focus on:
- Correctness: logic errors, missed edge cases, off-by-one errors.
- Time and space complexity of the approach (fill time_complexity and
  space_complexity with Big-O notation), and whether a more optimal approach exists.
- Whether it would hold up under typical contest time/memory limits.
""",
    Submission.Category.PRODUCTION: """
This is production/industry code. Focus on:
- Security: injection risks, unsafe input handling, secrets or credentials in code
  (fill security_notes).
- Scalability: what breaks under load or data growth (fill scalability_notes).
- Readability and maintainability for a team, not just the original author.
""",
    Submission.Category.LEARNING: """
This is a learning/personal project. Focus on:
- What the code does well given the apparent skill level.
- Readability and structure.
- Concrete, ordered next steps to improve it (fill suggested_next_steps) —
  tailored to whether the code looks beginner, intermediate, or advanced.
""",
}


def build_prompt(category, code_text):
    instructions = CATEGORY_INSTRUCTIONS[category]
    return f"""
You are an expert, experienced software engineer reviewing a peer's code.
Be honest and direct about problems — do not soften or sugar-coat feedback.

{instructions}

Code to review:
{code_text}

Respond with structured feedback: correctness/readability/best_practices notes,
a short list of top_improvements, and an overall_score from 0-10. Leave any
field that doesn't apply to this category as null rather than guessing.
"""
