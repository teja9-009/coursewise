"""Offline evaluation utilities for Coursewise recommendation experiments.

Metrics are calculated from human-labelled relevance data or real learner
outcomes. The module deliberately does not generate fake relevance labels.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import log2

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


class RecommendationEvaluator:
    """Calculate standard Top-K metrics for a set of recommendation cases."""

    def __init__(self, catalog_size: int, course_vectors=None):
        if catalog_size < 1:
            raise ValueError("catalog_size must be at least 1.")

        self.catalog_size = catalog_size
        self.course_vectors = course_vectors

    @staticmethod
    def _unique_ids(course_ids: Iterable) -> list[str]:
        return list(dict.fromkeys(str(course_id) for course_id in course_ids))

    @staticmethod
    def _metrics_at_k(recommended_ids: list[str], relevant_ids: set[str], k: int):
        top_k = recommended_ids[:k]
        hits = [course_id in relevant_ids for course_id in top_k]
        hit_count = sum(hits)

        precision = hit_count / k
        recall = hit_count / len(relevant_ids) if relevant_ids else 0.0

        dcg = sum(
            1 / log2(rank + 2)
            for rank, is_relevant in enumerate(hits)
            if is_relevant
        )
        ideal_hits = min(k, len(relevant_ids))
        idcg = sum(1 / log2(rank + 2) for rank in range(ideal_hits))
        ndcg = dcg / idcg if idcg else 0.0

        precision_sum = 0.0
        for rank, is_relevant in enumerate(hits, start=1):
            if is_relevant:
                precision_sum += sum(hits[:rank]) / rank
        average_precision = precision_sum / ideal_hits if ideal_hits else 0.0

        reciprocal_rank = 0.0
        for rank, is_relevant in enumerate(hits, start=1):
            if is_relevant:
                reciprocal_rank = 1 / rank
                break

        return {
            "precision": precision,
            "recall": recall,
            "ndcg": ndcg,
            "average_precision": average_precision,
            "reciprocal_rank": reciprocal_rank,
        }

    def evaluate(
        self,
        cases: Iterable[dict],
        k: int = 5,
    ) -> dict:
        """Evaluate labelled recommendation cases.

        Every case must contain ``recommended_course_ids`` and
        ``relevant_course_ids``. Relevant IDs should be from a lecturer's
        labels, a user study, or real saved/enrolled/completed outcomes.
        """
        if k < 1:
            raise ValueError("k must be at least 1.")

        case_metrics = []
        all_recommended_ids = set()
        diversity_values = []

        for case in cases:
            if "recommended_course_ids" not in case or "relevant_course_ids" not in case:
                raise ValueError(
                    "Each case needs recommended_course_ids and relevant_course_ids."
                )

            recommended_ids = self._unique_ids(case["recommended_course_ids"])
            relevant_ids = set(self._unique_ids(case["relevant_course_ids"]))
            metrics = self._metrics_at_k(recommended_ids, relevant_ids, k)
            case_metrics.append(metrics)
            all_recommended_ids.update(recommended_ids[:k])

            if "recommendation_vectors" in case:
                diversity_values.append(
                    self.diversity(case["recommendation_vectors"][:k])
                )

        if not case_metrics:
            raise ValueError("At least one labelled evaluation case is required.")

        report = {
            f"precision_at_{k}": float(np.mean([item["precision"] for item in case_metrics])),
            f"recall_at_{k}": float(np.mean([item["recall"] for item in case_metrics])),
            f"ndcg_at_{k}": float(np.mean([item["ndcg"] for item in case_metrics])),
            f"map_at_{k}": float(np.mean([item["average_precision"] for item in case_metrics])),
            f"mrr_at_{k}": float(np.mean([item["reciprocal_rank"] for item in case_metrics])),
            "coverage": len(all_recommended_ids) / self.catalog_size,
            "case_count": len(case_metrics),
        }

        if diversity_values:
            report["diversity"] = float(np.mean(diversity_values))

        return report

    @staticmethod
    def diversity(vectors) -> float:
        """Return average pairwise cosine distance for a recommendation list."""
        if len(vectors) < 2:
            return 0.0

        similarities = cosine_similarity(vectors)
        upper_triangle = similarities[np.triu_indices_from(similarities, k=1)]
        return float(np.mean(1 - upper_triangle)) if len(upper_triangle) else 0.0


def save_report(report: dict, output_path: str) -> None:
    """Write an evaluation report as a one-row CSV file for review evidence."""
    pd.DataFrame([report]).to_csv(output_path, index=False)
