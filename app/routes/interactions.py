from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Interaction, RecommendationLog

interactions_bp = Blueprint("interactions", __name__)


@interactions_bp.route("/save-course", methods=["POST"])
@login_required
def save_course():
    course_id = request.form.get("course_id", "")
    course_title = request.form.get("course_title", "")
    search_query = request.form.get("search_query", "")

    if not course_id or not course_title:
        flash("The course could not be saved.")
        return redirect(url_for("main.home"))

    interaction = Interaction(
        user_id=current_user.id,
        course_id=course_id,
        course_title=course_title,
        action="saved",
        search_query=search_query,
    )

    db.session.add(interaction)
    db.session.commit()

    flash(f'Saved "{course_title}" to your activity history.')
    return redirect(url_for("main.home"))


@interactions_bp.route("/activity")
@login_required
def activity():
    saved_courses = (
        Interaction.query
        .filter_by(user_id=current_user.id, action="saved")
        .order_by(Interaction.created_at.desc())
        .all()
    )

    search_history = (
        RecommendationLog.query
        .filter_by(user_id=current_user.id)
        .order_by(RecommendationLog.created_at.desc())
        .all()
    )

    return render_template(
        "activity.html",
        saved_courses=saved_courses,
        search_history=search_history,
    )
