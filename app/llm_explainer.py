import ollama

MODEL_NAME = "qwen3.5:9b"


def generate_explanation(interests, course):
    prompt = f"""
You are Coursewise, a helpful course recommendation assistant.

A learner is interested in: {interests}

Recommended course:
- Title: {course["title"]}
- Platform: {course["platform"]}
- Category: {course["category"]}
- Level: {course["level"]}
- Rating: {course["rating"]}

In exactly two short, friendly sentences, explain why this course is
a good match for the learner. Do not use bullet points or markdown.
"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response["message"]["content"].strip()

    except Exception:
        return (
            "This course matches your interests based on its topic, "
            "category, and recommendation score."
        )
