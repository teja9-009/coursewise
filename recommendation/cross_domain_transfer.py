"""Transfer learner preferences between Coursera and Udemy course domains."""

from __future__ import annotations

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class CrossDomainPreferenceTransfer:
    """Score a candidate using similar courses from another platform.

    A saved or completed Coursera course can therefore increase the score of
    semantically related Udemy courses, and the same works in reverse.
    """

    def __init__(self, courses, tfidf_matrix):
        self.courses = courses.reset_index(drop=True)
        self.tfidf_matrix = tfidf_matrix
        self.course_index = {
            str(course_id): index
            for index, course_id in enumerate(self.courses["course_id"].tolist())
        }

    def score_candidates(self, source_course_ids, candidates):
        """Return a 0–1 cross-platform similarity score for every candidate."""
        if not source_course_ids or candidates.empty:
            return np.zeros(len(candidates), dtype=float)

        candidate_ids = candidates["course_id"].astype(str).tolist()
        candidate_indices = [self.course_index.get(course_id) for course_id in candidate_ids]
        scores = np.zeros(len(candidates), dtype=float)

        for source_id in {str(course_id) for course_id in source_course_ids}:
            source_index = self.course_index.get(source_id)
            if source_index is None:
                continue
            source_platform = self.courses.iloc[source_index]["platform"]
            valid_positions = [
                position
                for position, candidate_index in enumerate(candidate_indices)
                if candidate_index is not None
                and self.courses.iloc[candidate_index]["platform"] != source_platform
            ]
            if not valid_positions:
                continue
            valid_indices = [candidate_indices[position] for position in valid_positions]
            similarities = cosine_similarity(
                self.tfidf_matrix[source_index],
                self.tfidf_matrix[valid_indices],
            ).flatten()
            for position, similarity in zip(valid_positions, similarities):
                scores[position] = max(scores[position], float(similarity))

        return scores
