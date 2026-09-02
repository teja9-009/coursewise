import pytest

from recommendation.evaluation import RecommendationEvaluator


def test_evaluator_calculates_standard_top_k_metrics():
    evaluator = RecommendationEvaluator(catalog_size=10)
    report = evaluator.evaluate(
        [
            {
                "recommended_course_ids": ["1", "2", "3"],
                "relevant_course_ids": ["1", "3", "9"],
            }
        ],
        k=3,
    )

    assert report["precision_at_3"] == pytest.approx(2 / 3)
    assert report["recall_at_3"] == pytest.approx(2 / 3)
    assert report["ndcg_at_3"] == pytest.approx(0.703918, abs=0.00001)
    assert report["map_at_3"] == pytest.approx(0.555556, abs=0.00001)
    assert report["mrr_at_3"] == 1.0
    assert report["coverage"] == pytest.approx(0.3)


def test_evaluator_requires_real_relevance_labels():
    evaluator = RecommendationEvaluator(catalog_size=10)

    with pytest.raises(ValueError, match="relevant_course_ids"):
        evaluator.evaluate([{"recommended_course_ids": ["1", "2"]}])


def test_diversity_is_zero_for_one_course():
    assert RecommendationEvaluator.diversity([[1, 0, 0]]) == 0.0
