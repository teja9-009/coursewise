import pandas as pd
import pytest

from recommendation.sequential_recommender import ActivitySequenceBuilder, GRU4RecLearner


def test_activity_sequences_follow_user_action_order():
    interactions = pd.DataFrame(
        [
            {"id": 1, "user_id": 1, "course_id": "python", "created_at": "2026-01-01"},
            {"id": 2, "user_id": 1, "course_id": "sql", "created_at": "2026-01-02"},
            {"id": 3, "user_id": 1, "course_id": "python", "created_at": "2026-01-03"},
            {"id": 4, "user_id": 2, "course_id": "excel", "created_at": "2026-01-01"},
        ]
    )

    assert ActivitySequenceBuilder.build(interactions) == [["python", "sql"]]


def test_training_samples_are_prefix_to_next_course_pairs():
    assert GRU4RecLearner.build_training_samples([["a", "b", "c"]]) == [(["a"], "b"), (["a", "b"], "c")]


def test_gru_training_requires_enough_user_activity():
    learner = GRU4RecLearner()
    interactions = pd.DataFrame(
        [{"user_id": 1, "course_id": "python", "created_at": "2026-01-01"}]
    )

    with pytest.raises(ValueError, match="Collect more"):
        learner.fit(interactions)
