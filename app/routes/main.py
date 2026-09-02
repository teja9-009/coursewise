from pathlib import Path
import sys
from urllib.parse import quote_plus

from flask import Blueprint, render_template, request
from flask_login import current_user

from app import db
from app.llm_explainer import generate_explanation
from app.models import RecommendationLog

project_root = Path(__file__).resolve().parents[2]
recommendation_folder = project_root / "recommendation"

if str(recommendation_folder) not in sys.path:
    sys.path.insert(0, str(recommendation_folder))

from recommender import CourseRecommender
from user_profile import UserProfile

main_bp = Blueprint("main", __name__)

PLATFORMS = ["All platforms", "Coursera", "Udemy"]
LEVELS = ["Any level", "Beginner", "Intermediate", "Advanced"]
CATEGORIES = [
    "Any category",
    "Business",
    "Computer Science",
    "Data Science",
    "Information Technology",
    "Language Learning",
    "Personal Development",
]


def create_course_search_link(course):
    title = quote_plus(course["title"])
    platform = course["platform"].lower()

    if platform == "coursera":
        return f"https://www.coursera.org/search?query={title}"

    if platform == "udemy":
        return f"https://www.udemy.com/courses/search/?q={title}"

    return ""


@main_bp.route("/legacy", methods=["GET", "POST"])
def home():
    interests = ""
    selected_platform = "All platforms"
    selected_level = "Any level"
    selected_category = "Any category"
    recommendations = []
    explanation = None
    error = None

    if request.method == "POST":
        interests = request.form.get("interests", "").strip()
        selected_platform = request.form.get("platform", "All platforms")
        selected_level = request.form.get("level", "Any level")
        selected_category = request.form.get("category", "Any category")

        if interests:
            try:
                preferred_platforms = (
                    ["Coursera", "Udemy"]
                    if selected_platform == "All platforms"
                    else [selected_platform]
                )

                preferred_level = (
                    None
                    if selected_level == "Any level"
                    else selected_level
                )

                preferred_categories = (
                    []
                    if selected_category == "Any category"
                    else [selected_category]
                )

                profile = UserProfile(
                    interests=interests,
                    preferred_level=preferred_level,
                    preferred_platforms=preferred_platforms,
                    preferred_categories=preferred_categories,
                )

                recommender = CourseRecommender()
                results = recommender.recommend(profile=profile, top_k=5)

                columns = [
                    "course_id",
                    "title",
                    "platform",
                    "category",
                    "level",
                    "rating",
                    "similarity",
                    "final_score",
                ]
                recommendations = (
                    results[columns]
                    .fillna("")
                    .to_dict(orient="records")
                )

                for course in recommendations:
                    course["course_link"] = create_course_search_link(course)

                search_log = RecommendationLog(
                    user_id=(
                        current_user.id
                        if current_user.is_authenticated
                        else None
                    ),
                    search_query=interests,
                    course_count=len(recommendations),
                )
                db.session.add(search_log)
                db.session.commit()

                if recommendations:
                    explanation = generate_explanation(
                        interests=interests,
                        course=recommendations[0],
                    )

            except Exception as exception:
                error = str(exception)
        else:
            error = "Please enter at least one interest."

    return render_template(
        "index.html",
        interests=interests,
        selected_platform=selected_platform,
        selected_level=selected_level,
        selected_category=selected_category,
        platforms=PLATFORMS,
        levels=LEVELS,
        categories=CATEGORIES,
        recommendations=recommendations,
        explanation=explanation,
        error=error,
    )
