"""
Personalized Ranking Module

Phase 2B

Current ranking signals:

1. TF-IDF similarity
2. Skill match
3. Level match
4. Category match
5. Rating quality

Future:
- Contrastive score
- GRU4Rec score
- Cross-domain score
- SHAP explanations
"""

import pandas as pd


class PersonalizedRanker:

    TFIDF_WEIGHT = 0.55
    SKILL_WEIGHT = 0.15
    LEVEL_WEIGHT = 0.10
    CATEGORY_WEIGHT = 0.10
    RATING_WEIGHT = 0.05
    CROSS_DOMAIN_WEIGHT = 0.05

    @staticmethod
    def skill_match(
        course_skills: str,
        user_text: str,
    ) -> float:

        if not user_text:
            return 0.0

        course_tokens = {
            token.strip().lower()
            for token in str(course_skills).split(",")
            if token.strip()
        }

        user_tokens = {
            token.strip().lower()
            for token in user_text.split()
            if token.strip()
        }

        if not course_tokens:
            return 0.0

        matches = 0

        for skill in course_tokens:

            for token in user_tokens:

                if token in skill:
                    matches += 1
                    break

        return min(matches / len(course_tokens), 1.0)

    @staticmethod
    def level_match(
        course_level: str,
        preferred_level: str | None,
    ) -> float:

        if not preferred_level:
            return 1.0

        course_level = str(course_level).strip()
        preferred_level = str(preferred_level).strip()

        if course_level == preferred_level:
            return 1.0

        if course_level in ["All Levels", "Mixed"]:
            return 0.5

        return 0.0

    @staticmethod
    def category_match(
        category: str,
        preferred_categories: list[str],
    ) -> float:

        if not preferred_categories:
            return 1.0

        category = str(category).strip().lower()

        preferred = {
            c.strip().lower()
            for c in preferred_categories
        }

        return 1.0 if category in preferred else 0.0

    @staticmethod
    def rating_score(rating) -> float:

        try:
            rating = float(rating)
        except Exception:
            return 0.0

        return max(
            0.0,
            min(rating / 5.0, 1.0),
        )

    def rank(
        self,
        candidates: pd.DataFrame,
        preferred_level: str | None,
        preferred_categories: list[str],
        user_profile_text: str,
        cross_domain_scores=None,
    ) -> pd.DataFrame:

        result = candidates.copy()

        result["skill_score"] = result["skills"].apply(
            lambda x: self.skill_match(
                x,
                user_profile_text,
            )
        )

        result["level_score"] = result["level"].apply(
            lambda x: self.level_match(
                x,
                preferred_level,
            )
        )

        result["category_score"] = result["category"].apply(
            lambda x: self.category_match(
                x,
                preferred_categories,
            )
        )

        result["rating_score"] = result["rating"].apply(
            self.rating_score
        )

        if cross_domain_scores is None:
            result["cross_domain_score"] = 0.0
        else:
            result["cross_domain_score"] = cross_domain_scores

        result["final_score"] = (
            self.TFIDF_WEIGHT * result["similarity"]
            + self.SKILL_WEIGHT * result["skill_score"]
            + self.LEVEL_WEIGHT * result["level_score"]
            + self.CATEGORY_WEIGHT * result["category_score"]
            + self.RATING_WEIGHT * result["rating_score"]
            + self.CROSS_DOMAIN_WEIGHT * result["cross_domain_score"]
        )

        result = result.sort_values(
            by="final_score",
            ascending=False,
        )

        return result.reset_index(drop=True)
