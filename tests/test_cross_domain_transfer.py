import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from recommendation.cross_domain_transfer import CrossDomainPreferenceTransfer


def test_cross_domain_transfer_only_scores_other_platform_candidates():
    courses = pd.DataFrame(
        [
            {"course_id": 1, "platform": "Coursera"},
            {"course_id": 2, "platform": "Udemy"},
            {"course_id": 3, "platform": "Coursera"},
        ]
    )
    vectors = csr_matrix(np.array([[1, 0], [0.9, 0.1], [1, 0]]))
    transfer = CrossDomainPreferenceTransfer(courses, vectors)
    candidates = pd.DataFrame({"course_id": [2, 3]})

    scores = transfer.score_candidates([1], candidates)

    assert scores[0] > 0.9
    assert scores[1] == 0
