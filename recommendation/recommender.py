"""
Phase 2B:
Personalized Top-K Recommendation Engine
"""

from pathlib import Path

import pandas as pd

try:
    # Package imports are used by automated tests and developer tooling.
    from .tfidf_engine import TFIDFEngine
    from .user_profile import UserProfile
    from .ranking import PersonalizedRanker
    from .profile_builder import ProfileBuilder
    from .cross_domain_transfer import CrossDomainPreferenceTransfer
except ImportError:
    # The deployed API loads this directory directly for backwards compatibility.
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

    @staticmethod
    def _ensure_platform_diversity(
        ranked: pd.DataFrame,
        preferred_platforms: list[str],
        top_k: int,
    ) -> pd.DataFrame:
        """Keep an all-platform search useful across both course providers.

        Ranking remains score-based, but a combined Coursera/Udemy search should
        not silently become a single-platform search when relevant matches from
        both providers are available.  Reserve up to two positions per provider,
        then fill any remaining positions with the next highest-scoring courses.
        """
        requested_platforms = {
            str(platform).strip().lower() for platform in preferred_platforms
        }
        supported_platforms = ("coursera", "udemy")

        if (
            top_k < 2
            or not set(supported_platforms).issubset(requested_platforms)
        ):
            return ranked.head(top_k).reset_index(drop=True)

        platform_matches = {
            platform: ranked[
                ranked["platform"].fillna("").str.lower().eq(platform)
            ]
            for platform in supported_platforms
        }

        if not all(not matches.empty for matches in platform_matches.values()):
            return ranked.head(top_k).reset_index(drop=True)

        reserved_per_platform = min(2, top_k // len(supported_platforms))
        reserved = pd.concat(
            [
                platform_matches[platform].head(reserved_per_platform)
                for platform in supported_platforms
            ]
        )
        remaining = ranked.loc[~ranked.index.isin(reserved.index)]
        balanced = pd.concat([reserved, remaining]).sort_values(
            by="final_score", ascending=False
        )

        return balanced.head(top_k).reset_index(drop=True)

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

        ranked = ranked.drop_duplicates(subset="title")
        return self._ensure_platform_diversity(
            ranked=ranked,
            preferred_platforms=profile.preferred_platforms,
            top_k=top_k,
        )
