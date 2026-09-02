"""
TF-IDF Course Representation Engine

Phase 2A of the Semantic Multi-Domain Course Recommendation System.

This module:
1. Loads the processed course feature dataset.
2. Converts course_text into TF-IDF vectors.
3. Provides course-level similarity search.
4. Supports cross-platform recommendations.
"""

from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TFIDFEngine:
    """Build and query TF-IDF representations of courses."""

    def __init__(
        self,
        data_path: str = "data/processed/course_features.csv",
        max_features: int = 10000,
        ngram_range: tuple = (1, 2),
        min_df: int = 1,
        max_df: float = 0.95,
    ):
        self.data_path = Path(data_path)
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df

        self.courses = None
        self.vectorizer = None
        self.tfidf_matrix = None

        self._load_data()
        self._build_tfidf()

    def _load_data(self):
        """Load course feature data."""

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Course feature dataset not found: {self.data_path}"
            )

        self.courses = pd.read_csv(self.data_path)

        required_columns = [
            "course_id",
            "canonical_course_id",
            "title",
            "platform",
            "category",
            "level",
            "skills",
            "course_text",
        ]

        missing = [
            column
            for column in required_columns
            if column not in self.courses.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required columns: {missing}"
            )

        self.courses["course_text"] = (
            self.courses["course_text"]
            .fillna("")
            .astype(str)
        )

    def _build_tfidf(self):
        """Create the TF-IDF representation."""

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            stop_words="english",
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            max_df=self.max_df,
            sublinear_tf=True,
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(
            self.courses["course_text"]
        )

    def get_course_index(self, course_id: int) -> int:
        """Return the matrix index for a course ID."""

        matches = self.courses.index[
            self.courses["course_id"] == course_id
        ].tolist()

        if not matches:
            raise ValueError(
                f"Course ID {course_id} not found."
            )

        return matches[0]

    def similar_courses(
        self,
        course_id: int,
        top_k: int = 10,
        exclude_same_platform: bool = False,
    ) -> pd.DataFrame:
        """
        Find courses similar to a given course.

        Parameters
        ----------
        course_id:
            ID of the source course.

        top_k:
            Number of recommendations.

        exclude_same_platform:
            If True, only return courses from other platforms.
        """

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        source_index = self.get_course_index(course_id)

        source_vector = self.tfidf_matrix[source_index]

        similarities = cosine_similarity(
            source_vector,
            self.tfidf_matrix,
        ).flatten()

        result = self.courses.copy()
        result["similarity"] = similarities

        # Never recommend the source course itself.
        result = result[
            result["course_id"] != course_id
        ]

        if exclude_same_platform:
            source_platform = self.courses.iloc[
                source_index
            ]["platform"]

            result = result[
                result["platform"] != source_platform
            ]

        result = result.sort_values(
            by="similarity",
            ascending=False,
        )

        return result.head(top_k).reset_index(drop=True)

    def search(
        self,
        query: str,
        top_k: int = 10,
        platform: str | None = None,
    ) -> pd.DataFrame:
        """
        Search the course catalog using natural-language interests.

        Example:
            search(
                "machine learning python artificial intelligence"
            )
        """

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        query_vector = self.vectorizer.transform([query])

        similarities = cosine_similarity(
            query_vector,
            self.tfidf_matrix,
        ).flatten()

        result = self.courses.copy()
        result["similarity"] = similarities

        if platform:
            result = result[
                result["platform"].str.lower()
                == platform.lower()
            ]

        result = result.sort_values(
            by="similarity",
            ascending=False,
        )

        return result.head(top_k).reset_index(drop=True)

    def cross_platform_search(
        self,
        query: str,
        top_k_per_platform: int = 5,
    ) -> pd.DataFrame:
        """
        Return recommendations separately from Coursera and Udemy.

        This is the first cross-domain recommendation capability.
        """

        coursera = self.search(
            query=query,
            top_k=top_k_per_platform,
            platform="Coursera",
        )

        udemy = self.search(
            query=query,
            top_k=top_k_per_platform,
            platform="Udemy",
        )

        coursera["recommendation_domain"] = "Coursera"
        udemy["recommendation_domain"] = "Udemy"

        return pd.concat(
            [coursera, udemy],
            ignore_index=True,
        )


if __name__ == "__main__":
    print("=" * 70)
    print("PHASE 2A - TF-IDF ENGINE TEST")
    print("=" * 70)

    engine = TFIDFEngine()

    print(f"Courses loaded: {len(engine.courses)}")
    print(f"TF-IDF matrix shape: {engine.tfidf_matrix.shape}")
    print(
        f"Vocabulary size: "
        f"{len(engine.vectorizer.vocabulary_)}"
    )

    print("\n=== SEARCH TEST ===")

    results = engine.search(
        "machine learning python artificial intelligence",
        top_k=10,
    )

    print(
        results[
            [
                "course_id",
                "title",
                "platform",
                "category",
                "level",
                "similarity",
            ]
        ].to_string(index=False)
    )

    print("\n=== CROSS-PLATFORM TEST ===")

    cross = engine.cross_platform_search(
        "machine learning python artificial intelligence",
        top_k_per_platform=5,
    )

    print(
        cross[
            [
                "course_id",
                "title",
                "platform",
                "similarity",
            ]
        ].to_string(index=False)
    )

    print("\nTF-IDF ENGINE TEST COMPLETE")
