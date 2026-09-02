"""Self-supervised contrastive learning for Coursewise course embeddings.

Positive pairs are courses in the same category and level. Other courses in a
training batch act as negatives, allowing the model to learn dense semantic
representations beyond sparse TF-IDF vectors.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _torch():
    """Load the optional training dependency only when it is needed."""
    try:
        import torch
        from torch import nn
    except ImportError as error:
        raise RuntimeError(
            "PyTorch is required for contrastive learning. Run: pip install -r requirements.txt"
        ) from error
    return torch, nn


def _make_encoder(input_size, embedding_size):
    """Create the same encoder architecture for training and model loading."""
    torch, nn = _torch()

    class Encoder(nn.Module):
        def __init__(self):
            super().__init__()
            hidden_size = min(512, max(128, input_size // 4))
            self.layers = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden_size, embedding_size),
            )

        def forward(self, values):
            return torch.nn.functional.normalize(self.layers(values), dim=1)

    return Encoder()


@dataclass
class ContrastiveTrainingConfig:
    embedding_size: int = 128
    batch_size: int = 64
    epochs: int = 20
    learning_rate: float = 1e-3
    temperature: float = 0.15
    random_seed: int = 42


class CourseContrastiveLearner:
    """Train and query course embeddings with an InfoNCE objective."""

    def __init__(self, config: ContrastiveTrainingConfig | None = None):
        self.config = config or ContrastiveTrainingConfig()
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            stop_words="english",
            max_features=5000,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.model = None
        self.course_embeddings = None
        self.course_ids = None
        self.course_metadata = None

    @staticmethod
    def build_positive_pairs(course_frame):
        """Create reproducible positive pairs from matching category and level."""
        random_generator = random.Random(42)
        pairs = []
        groups = course_frame.fillna("").groupby(["category", "level"])

        for _, group in groups:
            indices = group.index.tolist()
            if len(indices) < 2:
                continue
            for anchor in indices:
                candidates = [index for index in indices if index != anchor]
                pairs.append((anchor, random_generator.choice(candidates)))

        if not pairs:
            raise ValueError("No positive course pairs could be created from category and level.")
        return pairs

    @staticmethod
    def build_semantic_positive_pairs(course_frame, features):
        """Pair each course with its closest TF-IDF neighbour in its group.

        The category-and-level group keeps the pair pedagogically relevant;
        choosing the closest text neighbour prevents unrelated courses in a
        broad category from becoming artificial positives.
        """
        if isinstance(features, list):
            features = np.asarray(features)

        pairs = []
        groups = course_frame.fillna("").groupby(["category", "level"])

        for _, group in groups:
            indices = group.index.to_numpy()
            if len(indices) < 2:
                continue
            group_scores = cosine_similarity(features[indices])
            np.fill_diagonal(group_scores, -np.inf)
            for position, anchor in enumerate(indices):
                positive = indices[int(np.argmax(group_scores[position]))]
                pairs.append((int(anchor), int(positive)))

        if not pairs:
            raise ValueError("No semantic positive course pairs could be created.")
        return pairs

    @staticmethod
    def _info_nce_loss(embeddings, temperature):
        torch, _ = _torch()
        batch_size = embeddings.shape[0] // 2
        similarities = torch.matmul(embeddings, embeddings.T) / temperature
        diagonal = torch.eye(similarities.shape[0], device=embeddings.device).bool()
        similarities = similarities.masked_fill(diagonal, float("-inf"))
        targets = torch.cat(
            [
                torch.arange(batch_size, 2 * batch_size, device=embeddings.device),
                torch.arange(0, batch_size, device=embeddings.device),
            ]
        )
        return torch.nn.functional.cross_entropy(similarities, targets)

    def fit(self, course_frame):
        """Train a compact encoder from processed course data."""
        torch, nn = _torch()
        required = {"course_id", "course_text", "category", "level"}
        missing = required.difference(course_frame.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        frame = course_frame.reset_index(drop=True).copy()
        texts = frame["course_text"].fillna("").astype(str).tolist()
        features = self.vectorizer.fit_transform(texts).astype(np.float32).toarray()
        pairs = self.build_semantic_positive_pairs(frame, features)
        input_size = features.shape[1]
        if input_size == 0:
            raise ValueError("Course text did not produce any usable TF-IDF features.")

        random.seed(self.config.random_seed)
        np.random.seed(self.config.random_seed)
        torch.manual_seed(self.config.random_seed)

        self.model = _make_encoder(input_size, self.config.embedding_size)
        optimiser = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        feature_tensor = torch.tensor(features, dtype=torch.float32)
        losses = []

        for _ in range(self.config.epochs):
            random.shuffle(pairs)
            epoch_losses = []
            for start in range(0, len(pairs), self.config.batch_size):
                batch_pairs = pairs[start : start + self.config.batch_size]
                if len(batch_pairs) < 2:
                    continue
                anchors = torch.stack([feature_tensor[left] for left, _ in batch_pairs])
                positives = torch.stack([feature_tensor[right] for _, right in batch_pairs])
                embeddings = self.model(torch.cat([anchors, positives]))
                loss = self._info_nce_loss(embeddings, self.config.temperature)
                optimiser.zero_grad()
                loss.backward()
                optimiser.step()
                epoch_losses.append(float(loss.detach()))
            losses.append(float(np.mean(epoch_losses)) if epoch_losses else 0.0)

        self.model.eval()
        with torch.no_grad():
            self.course_embeddings = self.model(feature_tensor).cpu().numpy()
        self.course_ids = frame["course_id"].astype(str).tolist()
        self.course_metadata = frame
        return {"pair_count": len(pairs), "losses": losses, "embedding_size": self.config.embedding_size}

    def save(self, output_path):
        """Save the trained model, TF-IDF vocabulary, embeddings, and catalogue IDs."""
        if self.model is None or self.course_embeddings is None:
            raise RuntimeError("Train the contrastive learner before saving it.")

        torch, _ = _torch()
        torch.save(
            {
                "config": self.config.__dict__,
                "model_state": self.model.state_dict(),
                "input_size": len(self.vectorizer.vocabulary_),
                "vectorizer": self.vectorizer,
                "course_embeddings": self.course_embeddings,
                "course_ids": self.course_ids,
                "course_metadata": self.course_metadata,
            },
            output_path,
        )

    @classmethod
    def load(cls, input_path):
        """Restore a local model created with :meth:`save`."""
        torch, _ = _torch()
        payload = torch.load(input_path, map_location="cpu", weights_only=False)
        learner = cls(ContrastiveTrainingConfig(**payload["config"]))
        learner.model = _make_encoder(payload["input_size"], learner.config.embedding_size)
        learner.model.load_state_dict(payload["model_state"])
        learner.model.eval()
        learner.vectorizer = payload["vectorizer"]
        learner.course_embeddings = payload["course_embeddings"]
        learner.course_ids = payload["course_ids"]
        learner.course_metadata = payload["course_metadata"]
        return learner

    def similar_courses(self, course_id, top_k=5, cross_platform=False):
        """Return dense-embedding neighbours for a trained model."""
        if self.course_embeddings is None or self.course_metadata is None:
            raise RuntimeError("Train the contrastive learner before requesting recommendations.")

        course_id = str(course_id)
        try:
            source_index = self.course_ids.index(course_id)
        except ValueError as error:
            raise ValueError(f"Course ID {course_id} not found.") from error

        scores = cosine_similarity(self.course_embeddings[source_index : source_index + 1], self.course_embeddings).flatten()
        result = self.course_metadata.copy()
        result["contrastive_similarity"] = scores
        result = result[result["course_id"].astype(str) != course_id]

        if cross_platform:
            source_platform = self.course_metadata.iloc[source_index]["platform"]
            result = result[result["platform"] != source_platform]

        return result.sort_values("contrastive_similarity", ascending=False).head(top_k).reset_index(drop=True)
