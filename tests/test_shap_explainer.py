from recommendation.shap_explainer import CoursewiseShapExplainer


def test_exact_shap_values_are_sorted_by_ranking_contribution():
    explanation = CoursewiseShapExplainer().explain(
        {
            "similarity": 0.8,
            "skill_score": 1.0,
            "level_score": 1.0,
            "category_score": 0.0,
            "rating_score": 1.0,
            "cross_domain_score": 0.5,
        }
    )

    assert explanation[0] == {"factor": "semantic similarity", "shap_value": 0.44}
    assert explanation[1] == {"factor": "skill match", "shap_value": 0.15}
    assert explanation[2] == {"factor": "level match", "shap_value": 0.1}
