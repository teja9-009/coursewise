from pathlib import Path
import os
import re
import secrets
import sys
from urllib.parse import quote_plus

from flask import Blueprint, current_app, jsonify, redirect, request, session
from flask_login import current_user, login_user, logout_user

from app import db, oauth
from app.llm_explainer import generate_explanation
from app.models import Interaction, RecommendationLog, User

project_root = Path(__file__).resolve().parents[2]
recommendation_folder = project_root / "recommendation"

if str(recommendation_folder) not in sys.path:
    sys.path.insert(0, str(recommendation_folder))

from recommender import CourseRecommender
from user_profile import UserProfile
from shap_explainer import CoursewiseShapExplainer

api_bp = Blueprint("api", __name__, url_prefix="/api")


def course_search_link(course):
    title = quote_plus(course["title"])
    platform = course["platform"].lower()

    if platform == "coursera":
        return f"https://www.coursera.org/search?query={title}"

    if platform == "udemy":
        return f"https://www.udemy.com/courses/search/?q={title}"

    return ""


def interaction_course_ids(action):
    if not current_user.is_authenticated:
        return []

    interactions = Interaction.query.filter_by(
        user_id=current_user.id,
        action=action,
    ).all()
    course_ids = []

    for interaction in interactions:
        try:
            course_ids.append(int(interaction.course_id))
        except (TypeError, ValueError):
            continue

    return course_ids


def current_user_data():
    if not current_user.is_authenticated:
        return None

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "learning_status": current_user.learning_status or "",
        "learning_level": current_user.learning_level or "",
        "learning_goal": current_user.learning_goal or "",
        "skills": current_user.skills or "",
    }


def frontend_url():
    return os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def redirect_to_frontend_with_error(message):
    return redirect(f"{frontend_url()}/?google_error={quote_plus(message)}")


def redirect_to_frontend_after_google_login():
    return redirect(f"{frontend_url()}/?google_login=success")


def google_username(name, email):
    preferred_name = name or email.split("@", maxsplit=1)[0]
    base_name = re.sub(r"[^a-zA-Z0-9_-]", "", preferred_name).lower()
    base_name = base_name[:60] or "google-user"
    candidate = base_name

    while User.query.filter_by(username=candidate).first():
        candidate = f"{base_name[:50]}-{secrets.token_hex(4)}"

    return candidate


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.get("/me")
def get_current_user():
    return jsonify({"user": current_user_data()})


@api_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not username or not email or not password:
        return jsonify({"error": "Please complete every field."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "That username is already in use."}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "That email address is already registered."}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)
    session.permanent = True

    return jsonify({"user": current_user_data()}), 201


@api_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Incorrect email address or password."}), 401

    login_user(user, remember=True)
    session.permanent = True
    return jsonify({"user": current_user_data()})


@api_bp.post("/auth/logout")
def logout():
    logout_user()
    session.clear()
    return jsonify({"message": "Logged out."})


@api_bp.get("/auth/google")
def google_login():
    google = oauth.create_client("google")
    if google is None:
        return redirect_to_frontend_with_error(
            "Google sign-in has not been configured yet."
        )

    redirect_uri = os.environ.get(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:5000/api/auth/google/callback",
    )
    return google.authorize_redirect(redirect_uri)


@api_bp.get("/auth/google/callback")
def google_callback():
    google = oauth.create_client("google")
    if google is None:
        return redirect_to_frontend_with_error(
            "Google sign-in has not been configured yet."
        )

    try:
        token = google.authorize_access_token()
        userinfo = token.get("userinfo") or google.parse_id_token(token)
    except Exception:
        return redirect_to_frontend_with_error(
            "Google sign-in could not be completed. Please try again."
        )

    email = str(userinfo.get("email", "")).strip().lower()
    if not email or not userinfo.get("email_verified"):
        return redirect_to_frontend_with_error(
            "Google did not provide a verified email address."
        )

    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            username=google_username(userinfo.get("name", ""), email),
            email=email,
        )
        user.set_password(secrets.token_urlsafe(32))
        db.session.add(user)
        db.session.commit()

    login_user(user, remember=True)
    session.permanent = True
    return redirect_to_frontend_after_google_login()


@api_bp.put("/profile")
def update_profile():
    if not current_user.is_authenticated:
        return jsonify({"error": "Please log in to edit your profile."}), 401

    data = request.get_json(silent=True) or {}
    current_user.learning_status = str(data.get("learning_status", "")).strip()[:80]
    current_user.learning_level = str(data.get("learning_level", "")).strip()[:80]
    current_user.learning_goal = str(data.get("learning_goal", "")).strip()[:300]
    current_user.skills = str(data.get("skills", "")).strip()[:500]
    db.session.commit()

    return jsonify(
        {
            "message": "Your learning profile has been updated.",
            "user": current_user_data(),
        }
    )


@api_bp.post("/recommendations")
def recommendations():
    data = request.get_json(silent=True) or {}
    interests = str(data.get("interests", "")).strip()
    platform = str(data.get("platform", "All platforms"))
    level = str(data.get("level", "Any level"))
    category = str(data.get("category", "Any category"))

    if not interests:
        return jsonify({"error": "Please enter at least one interest."}), 400

    preferred_platforms = (
        ["Coursera", "Udemy"]
        if platform == "All platforms"
        else [platform]
    )
    preferred_level = None if level == "Any level" else level
    preferred_categories = [] if category == "Any category" else [category]

    profile_level = (
        current_user.learning_level
        if current_user.is_authenticated
        else ""
    )
    effective_level = preferred_level or profile_level or None

    profile = UserProfile(
        interests=interests,
        learning_goal=(
            current_user.learning_goal
            if current_user.is_authenticated
            else ""
        ),
        skills=(current_user.skills if current_user.is_authenticated else ""),
        learning_status=(
            current_user.learning_status
            if current_user.is_authenticated
            else ""
        ),
        preferred_level=effective_level,
        preferred_platforms=preferred_platforms,
        preferred_categories=preferred_categories,
        liked_courses=interaction_course_ids("saved"),
        completed_courses=interaction_course_ids("completed"),
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
        "final_score",
        "similarity",
        "skill_score",
        "level_score",
        "category_score",
        "rating_score",
        "cross_domain_score",
    ]
    courses = results.reindex(columns=columns).fillna("").to_dict(orient="records")
    shap_explainer = CoursewiseShapExplainer()

    for course in courses:
        course["course_link"] = course_search_link(course)
        course["explanation_factors"] = shap_explainer.explain(course)

    search_log = RecommendationLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        search_query=interests,
        course_count=len(courses),
    )
    db.session.add(search_log)
    db.session.commit()

    explanation = ""
    if courses:
        explanation = generate_explanation(interests=interests, course=courses[0])

    return jsonify(
        {
            "recommendations": courses,
            "explanation": explanation,
        }
    )


@api_bp.post("/saved-courses")
def save_course():
    return create_course_action("saved")


@api_bp.post("/course-actions/<action>")
def course_action(action):
    if action not in {"enrolled", "completed"}:
        return jsonify({"error": "Unsupported course action."}), 400

    return create_course_action(action)


@api_bp.delete("/saved-courses/<int:interaction_id>")
def remove_saved_course(interaction_id):
    if not current_user.is_authenticated:
        return jsonify({"error": "Please log in to manage saved courses."}), 401

    interaction = db.session.get(Interaction, interaction_id)

    if (
        not interaction
        or interaction.user_id != current_user.id
        or interaction.action != "saved"
    ):
        return jsonify({"error": "Saved course not found."}), 404

    course_title = interaction.course_title
    db.session.delete(interaction)
    db.session.commit()

    return jsonify({"message": f'Removed "{course_title}" from saved courses.'})


def create_course_action(action):
    if not current_user.is_authenticated:
        return jsonify({"error": "Please log in to track course activity."}), 401

    data = request.get_json(silent=True) or {}
    course_id = str(data.get("course_id", ""))
    course_title = str(data.get("course_title", ""))
    search_query = str(data.get("search_query", ""))

    if not course_id or not course_title:
        return jsonify({"error": "The course could not be tracked."}), 400

    existing_interaction = Interaction.query.filter_by(
        user_id=current_user.id,
        course_id=course_id,
        action=action,
    ).first()
    if existing_interaction:
        return jsonify(
            {
                "message": f'"{course_title}" is already marked as {action}.',
                "already_exists": True,
            }
        )

    interaction = Interaction(
        user_id=current_user.id,
        course_id=course_id,
        course_title=course_title,
        action=action,
        search_query=search_query,
    )
    db.session.add(interaction)
    db.session.commit()

    action_message = {
        "saved": "Saved",
        "enrolled": "Marked as enrolled",
        "completed": "Marked as completed",
    }[action]

    return jsonify({"message": f'{action_message} "{course_title}".'}), 201


@api_bp.get("/activity")
def activity():
    if not current_user.is_authenticated:
        return jsonify({"error": "Please log in to view activity."}), 401

    def course_actions(action):
        return (
            Interaction.query
            .filter_by(user_id=current_user.id, action=action)
            .order_by(Interaction.created_at.desc())
            .all()
        )

    def serialize_courses(interactions):
        return [
            {
                "id": item.id,
                "course_id": item.course_id,
                "course_title": item.course_title,
                "search_query": item.search_query,
                "created_at": item.created_at.isoformat(),
            }
            for item in interactions
        ]

    saved_courses = course_actions("saved")
    enrolled_courses = course_actions("enrolled")
    completed_courses = course_actions("completed")
    search_history = (
        RecommendationLog.query
        .filter_by(user_id=current_user.id)
        .order_by(RecommendationLog.created_at.desc())
        .all()
    )

    return jsonify(
        {
            "summary": {
                "saved": len(saved_courses),
                "enrolled": len(enrolled_courses),
                "completed": len(completed_courses),
            },
            "saved_courses": serialize_courses(saved_courses),
            "enrolled_courses": serialize_courses(enrolled_courses),
            "completed_courses": serialize_courses(completed_courses),
            "search_history": [
                {
                    "id": item.id,
                    "search_query": item.search_query,
                    "course_count": item.course_count,
                    "created_at": item.created_at.isoformat(),
                }
                for item in search_history
            ],
        }
    )
