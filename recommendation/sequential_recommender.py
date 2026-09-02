"""GRU4Rec-style next-course recommendation from learner activity sequences."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np


def _torch():
    try:
        import torch
        from torch import nn
    except ImportError as error:
        raise RuntimeError(
            "PyTorch is required for sequential learning. Run: pip install -r requirements.txt"
        ) from error
    return torch, nn


@dataclass
class GRU4RecConfig:
    embedding_size: int = 64
    hidden_size: int = 96
    batch_size: int = 32
    epochs: int = 20
    learning_rate: float = 1e-3
    random_seed: int = 42


class ActivitySequenceBuilder:
    """Convert timestamped user actions into ordered course sequences."""

    REQUIRED_COLUMNS = {"user_id", "course_id", "created_at"}

    @classmethod
    def build(cls, interactions):
        missing = cls.REQUIRED_COLUMNS.difference(interactions.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        frame = interactions.dropna(subset=["user_id", "course_id"]).copy()
        frame["course_id"] = frame["course_id"].astype(str)
        sort_columns = ["user_id", "created_at"]
        if "id" in frame.columns:
            sort_columns.append("id")
        frame = frame.sort_values(sort_columns)

        sequences = []
        for _, user_actions in frame.groupby("user_id"):
            sequence = list(dict.fromkeys(user_actions["course_id"].tolist()))
            if len(sequence) >= 2:
                sequences.append(sequence)
        return sequences


def _make_model(vocabulary_size, config):
    torch, nn = _torch()

    class GRU4Rec(nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = nn.Embedding(vocabulary_size, config.embedding_size, padding_idx=0)
            self.gru = nn.GRU(config.embedding_size, config.hidden_size, batch_first=True)
            self.output = nn.Linear(config.hidden_size, vocabulary_size)

        def forward(self, sequence):
            embedded = self.embedding(sequence)
            _, hidden = self.gru(embedded)
            return self.output(hidden[-1])

    return GRU4Rec()


class GRU4RecLearner:
    """Train a next-course recommender from activity sequences."""

    def __init__(self, config: GRU4RecConfig | None = None):
        self.config = config or GRU4RecConfig()
        self.model = None
        self.course_to_index = None
        self.index_to_course = None

    @staticmethod
    def build_training_samples(sequences):
        """Create prefix → next-course samples from every learner sequence."""
        return [
            (sequence[:position], sequence[position])
            for sequence in sequences
            for position in range(1, len(sequence))
        ]

    def fit(self, interactions):
        torch, _ = _torch()
        sequences = ActivitySequenceBuilder.build(interactions)
        samples = self.build_training_samples(sequences)
        if len(samples) < 2:
            raise ValueError(
                "GRU4Rec needs at least two next-course training samples. "
                "Collect more saved, enrolled, or completed course activity first."
            )

        all_course_ids = sorted({course_id for sequence in sequences for course_id in sequence})
        self.course_to_index = {course_id: index + 1 for index, course_id in enumerate(all_course_ids)}
        self.index_to_course = {index: course_id for course_id, index in self.course_to_index.items()}
        self.model = _make_model(len(self.course_to_index) + 1, self.config)
        optimiser = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        loss_function = torch.nn.CrossEntropyLoss()
        np.random.seed(self.config.random_seed)
        torch.manual_seed(self.config.random_seed)
        losses = []

        for _ in range(self.config.epochs):
            np.random.shuffle(samples)
            epoch_losses = []
            for start in range(0, len(samples), self.config.batch_size):
                batch = samples[start : start + self.config.batch_size]
                sequence_length = max(len(prefix) for prefix, _ in batch)
                input_rows = [
                    [0] * (sequence_length - len(prefix)) + [self.course_to_index[item] for item in prefix]
                    for prefix, _ in batch
                ]
                targets = [self.course_to_index[target] for _, target in batch]
                logits = self.model(torch.tensor(input_rows, dtype=torch.long))
                loss = loss_function(logits, torch.tensor(targets, dtype=torch.long))
                optimiser.zero_grad()
                loss.backward()
                optimiser.step()
                epoch_losses.append(float(loss.detach()))
            losses.append(float(np.mean(epoch_losses)))

        self.model.eval()
        return {"sequence_count": len(sequences), "sample_count": len(samples), "losses": losses}

    def recommend_next(self, course_history, top_k=5):
        """Recommend unseen next courses after a learner's activity history."""
        if self.model is None:
            raise RuntimeError("Train GRU4Rec before requesting next-course recommendations.")
        if not course_history:
            return []

        torch, _ = _torch()
        known_history = [str(course_id) for course_id in course_history if str(course_id) in self.course_to_index]
        if not known_history:
            return []

        sequence = torch.tensor([[self.course_to_index[course] for course in known_history]], dtype=torch.long)
        with torch.no_grad():
            scores = self.model(sequence).flatten()
        for course_id in set(known_history):
            scores[self.course_to_index[course_id]] = float("-inf")
        top_indices = torch.topk(scores, min(top_k, len(self.course_to_index))).indices.tolist()
        return [self.index_to_course[index] for index in top_indices if index in self.index_to_course]
