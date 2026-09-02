# Coursewise evaluation labels

This folder is for the labelled test cases used to evaluate recommendation
experiments. Each case needs:

```json
{
  "query": "python for beginners",
  "recommended_course_ids": ["101", "202", "303"],
  "relevant_course_ids": ["101", "303"]
}
```

`relevant_course_ids` must be supplied by a learner study, a faculty review,
or real learner outcomes such as saved, enrolled, and completed courses. Do
not create labels from the model's own output, because that would make the
evaluation misleading.
