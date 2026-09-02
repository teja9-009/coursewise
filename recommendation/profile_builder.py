"""
Profile Builder

Phase 2B.1

Builds an enriched semantic user profile using:

- Explicit interests
- Viewed courses
- Liked courses
- Completed courses
"""

from pathlib import Path

import pandas as pd

from user_profile import UserProfile


class ProfileBuilder:

    def __init__(
        self,
        data_path="data/processed/courses_clean.csv",
    ):
        self.courses = pd.read_csv(
            Path(data_path)
        )

    def _get_course_texts(
        self,
        course_ids: list[int],
    ) -> list[str]:

        if not course_ids:
            return []

        rows = self.courses[
            self.courses["course_id"].isin(course_ids)
        ]

        texts = []

        for _, row in rows.iterrows():

            texts.append(
                str(row.get("title", ""))
            )

            texts.append(
                str(row.get("category", ""))
            )

            texts.append(
                str(row.get("skills", ""))
            )

        return texts

    def build_query(
        self,
        profile: UserProfile,
    ) -> str:
        """
        Build an enriched semantic query.
        """

        parts = []

        if profile.interests:
            parts.append(profile.interests)

        if profile.learning_goal:
            parts.append(profile.learning_goal)

        if profile.skills:
            parts.append(profile.skills)

        if profile.learning_status:
            parts.append(profile.learning_status)

        parts.extend(
            self._get_course_texts(
                profile.viewed_courses
            )
        )

        parts.extend(
            self._get_course_texts(
                profile.liked_courses
            )
        )

        parts.extend(
            self._get_course_texts(
                profile.completed_courses
            )
        )

        return " ".join(
            str(p).strip()
            for p in parts
            if str(p).strip()
        )
