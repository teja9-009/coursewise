"""Exact Shapley-value explanations for Coursewise's additive baseline ranker.

The baseline score is a weighted sum of independent ranking features. With a
zero-feature baseline, every feature's exact Shapley value is simply its
weight multiplied by its observed score. This gives transparent, reproducible
attributions without inventing an opaque explanation.
"""

from __future__ import annotations


class CoursewiseShapExplainer:
    """Convert ranking signals into user-readable Shapley contributions."""

    FEATURES = (
        ("semantic similarity", "similarity", 0.55),
        ("skill match", "skill_score", 0.15),
        ("level match", "level_score", 0.10),
        ("category match", "category_score", 0.10),
        ("course rating", "rating_score", 0.05),
        ("cross-platform learning history", "cross_domain_score", 0.05),
    )

    @staticmethod
    def _number(value):
        try:
            return max(0.0, min(float(value), 1.0))
        except (TypeError, ValueError):
            return 0.0

    def explain(self, course, top_n=3):
        contributions = [
            {
                "factor": label,
                "shap_value": round(weight * self._number(course.get(key)), 4),
            }
            for label, key, weight in self.FEATURES
        ]
        contributions = [item for item in contributions if item["shap_value"] > 0]
        return sorted(contributions, key=lambda item: item["shap_value"], reverse=True)[:top_n]
