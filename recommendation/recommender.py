"""
Phase 2B:
Personalized Top-K Recommendation Engine
"""

from pathlib import Path

import pandas as pd

from tfidf_engine import TFIDFEngine
from user_profile import UserProfile
from ranking import PersonalizedRanker
from profile_builder import ProfileBuilder
from cross_domain_transfer import CrossDomainPreferenceTransfer


class CourseRecommender:
    def __init__(self):
        self.engine = TFIDFEngine()
        self.ranker = PersonalizedRanker()
        self.profile_builder = ProfileBuilder()
        self.course_metadata = pd.read_csv(
            Path("data/processed/courses_clean.csv")
        )
        self.cross_domain_transfer = CrossDomainPreferenceTransfer(
            self.engine.courses,
            self.engine.tfidf_matrix,
        )

    def recommend(self, profile: UserProfile, top_k: int = 10):
        query = self.profile_builder.build_query(profile)

        candidates = self.engine.search(
            query=query,
            top_k=100,
        )

        candidates = candidates.drop_duplicates(subset="course_id")

        metadata_columns = [
            "course_id",
            "rating",
            "reviews",
            "instructor",
            "learning_product",
            "url",
        ]
        unique_metadata = self.course_metadata[metadata_columns].drop_duplicates(
            subset="course_id"
        )

        candidates = candidates.merge(
            unique_metadata,
            on="course_id",
            how="left",
        )

        if profile.preferred_platforms:
            allowed_platforms = {
                platform.lower()
                for platform in profile.preferred_platforms
            }
            candidates = candidates[
                candidates["platform"]
                .fillna("")
                .str.lower()
                .isin(allowed_platforms)
            ]

        if profile.preferred_level:
            candidates = candidates[
                candidates["level"]
                .fillna("")
                .str.lower()
                .eq(profile.preferred_level.lower())
            ]

        if profile.preferred_categories:
            allowed_categories = {
                category.lower()
                for category in profile.preferred_categories
            }
            candidates = candidates[
                candidates["category"]
                .fillna("")
                .str.lower()
                .isin(allowed_categories)
            ]

        activity_course_ids = profile.liked_courses + profile.completed_courses
        cross_domain_scores = self.cross_domain_transfer.score_candidates(
            activity_course_ids,
            candidates,
        )

        ranked = self.ranker.rank(
            candidates=candidates,
            preferred_level=profile.preferred_level,
            preferred_categories=profile.preferred_categories,
            user_profile_text=query,
            cross_domain_scores=cross_domain_scores,
        )

        return ranked.drop_duplicates(subset="title").head(top_k)
