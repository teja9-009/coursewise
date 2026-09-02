"""
User Profile Representation

Phase 2B:
Personalized Recommendation Layer
"""

from dataclasses import dataclass, field


@dataclass
class UserProfile:
    """
    Stores user learning preferences.
    """

    interests: str

    learning_goal: str = ""

    skills: str = ""

    learning_status: str = ""

    preferred_level: str | None = None

    preferred_platforms: list[str] = field(
        default_factory=list
    )

    preferred_categories: list[str] = field(
        default_factory=list
    )

    viewed_courses: list[int] = field(
        default_factory=list
    )

    liked_courses: list[int] = field(
        default_factory=list
    )

    completed_courses: list[int] = field(
        default_factory=list
    )

    def to_query_text(self) -> str:
        """
        Convert profile into a semantic query
        for TF-IDF retrieval.
        """

        parts = []

        if self.interests:
            parts.append(self.interests)

        if self.preferred_categories:
            parts.extend(self.preferred_categories)

        if self.preferred_level:
            parts.append(self.preferred_level)

        return " ".join(parts)
