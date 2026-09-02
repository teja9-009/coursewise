import pandas as pd
import pytest

from recommendation.contrastive_learning import CourseContrastiveLearner


def test_positive_pairs_use_matching_category_and_level():
    courses = pd.DataFrame(
        [
            {"course_id": 1, "course_text": "python basics", "category": "Computer Science", "level": "Beginner"},
            {"course_id": 2, "course_text": "python loops", "category": "Computer Science", "level": "Beginner"},
            {"course_id": 3, "course_text": "business law", "category": "Business", "level": "Intermediate"},
        ]
    )

    pairs = CourseContrastiveLearner.build_positive_pairs(courses)

    assert pairs == [(0, 1), (1, 0)]


def test_semantic_pairs_choose_the_closest_course_in_each_group():
    courses = pd.DataFrame(
        [
            {"course_id": 1, "course_text": "python basics", "category": "Computer Science", "level": "Beginner"},
            {"course_id": 2, "course_text": "python loops", "category": "Computer Science", "level": "Beginner"},
            {"course_id": 3, "course_text": "business planning", "category": "Business", "level": "Intermediate"},
        ]
    )
    features = [[1, 0], [0.9, 0.1], [0, 1]]

    assert CourseContrastiveLearner.build_semantic_positive_pairs(courses, features) == [(0, 1), (1, 0)]


def test_fit_explains_when_pytorch_is_not_installed():
    learner = CourseContrastiveLearner()
    courses = pd.DataFrame(
        [
            {"course_id": 1, "course_text": "python basics", "category": "Computer Science", "level": "Beginner"},
            {"course_id": 2, "course_text": "python loops", "category": "Computer Science", "level": "Beginner"},
        ]
    )

    try:
        import torch  # noqa: F401
    except ImportError:
        with pytest.raises(RuntimeError, match="PyTorch"):
            learner.fit(courses)
