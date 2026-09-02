import pandas as pd
import pytest

from app import create_app, db


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    database_path = tmp_path / "coursewise-test.db"
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "coursewise-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client):
    return client.post(
        "/api/auth/register",
        json={
            "username": "test-learner",
            "email": "learner@example.com",
            "password": "secure-password",
        },
    )


def course_payload(course_id="course-101"):
    return {
        "course_id": course_id,
        "course_title": "Python for Data Analysis",
        "search_query": "python data",
    }


def test_registration_logs_the_user_in_and_returns_their_profile(client):
    response = register(client)

    assert response.status_code == 201
    assert response.json["user"]["username"] == "test-learner"

    me_response = client.get("/api/me")
    assert me_response.status_code == 200
    assert me_response.json["user"]["email"] == "learner@example.com"


def test_profile_update_is_saved_for_the_logged_in_user(client):
    register(client)

    response = client.put(
        "/api/profile",
        json={
            "learning_status": "Building projects",
            "learning_level": "Intermediate",
            "learning_goal": "Become a data analyst",
            "skills": "Python, Excel, SQL",
        },
    )

    assert response.status_code == 200
    assert response.json["user"]["learning_level"] == "Intermediate"
    assert response.json["user"]["skills"] == "Python, Excel, SQL"


def test_google_sign_in_returns_to_the_dashboard_when_not_configured(client):
    response = client.get("/api/auth/google", follow_redirects=False)

    assert response.status_code == 302
    assert "google_error=Google+sign-in+has+not+been+configured+yet." in response.location


def test_course_actions_are_tracked_once_and_appear_in_activity(client):
    register(client)

    saved_response = client.post("/api/saved-courses", json=course_payload())
    duplicate_saved_response = client.post("/api/saved-courses", json=course_payload())
    enrolled_response = client.post(
        "/api/course-actions/enrolled", json=course_payload()
    )
    completed_response = client.post(
        "/api/course-actions/completed", json=course_payload()
    )

    assert saved_response.status_code == 201
    assert duplicate_saved_response.status_code == 200
    assert duplicate_saved_response.json["already_exists"] is True
    assert enrolled_response.status_code == 201
    assert completed_response.status_code == 201

    activity_response = client.get("/api/activity")
    activity = activity_response.json
    assert activity_response.status_code == 200
    assert activity["summary"] == {"saved": 1, "enrolled": 1, "completed": 1}
    assert activity["saved_courses"][0]["course_title"] == "Python for Data Analysis"
    assert len(activity["enrolled_courses"]) == 1
    assert len(activity["completed_courses"]) == 1


def test_recommendations_return_courses_and_create_search_history(client, monkeypatch):
    register(client)

    class FakeRecommender:
        def recommend(self, profile, top_k):
            return pd.DataFrame(
                [
                    {
                        "course_id": 7,
                        "title": "Python Foundations",
                        "platform": "Coursera",
                        "category": "Data Science",
                        "level": "Beginner",
                        "rating": 4.8,
                        "final_score": 0.91,
                    }
                ]
            )

    monkeypatch.setattr("app.routes.api.CourseRecommender", FakeRecommender)
    monkeypatch.setattr(
        "app.routes.api.generate_explanation",
        lambda interests, course: "A strong starting point for Python.",
    )

    response = client.post(
        "/api/recommendations",
        json={
            "interests": "python",
            "platform": "All platforms",
            "level": "Any level",
            "category": "Any category",
        },
    )

    assert response.status_code == 200
    assert response.json["recommendations"][0]["title"] == "Python Foundations"
    assert response.json["explanation"] == "A strong starting point for Python."

    activity_response = client.get("/api/activity")
    assert activity_response.json["search_history"][0]["search_query"] == "python"
