"""Train and save Coursewise's contrastive course-representation model."""

from pathlib import Path

import pandas as pd

from contrastive_learning import CourseContrastiveLearner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "course_features.csv"
MODEL_PATH = PROJECT_ROOT / "data" / "models" / "coursewise_contrastive.pt"


def main():
    courses = pd.read_csv(DATA_PATH)
    learner = CourseContrastiveLearner()
    report = learner.fit(courses)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    learner.save(MODEL_PATH)
    print(f"Trained course pairs: {report['pair_count']}")
    print(f"Final training loss: {report['losses'][-1]:.4f}")
    print(f"Saved model: {MODEL_PATH}")


if __name__ == "__main__":
    main()
