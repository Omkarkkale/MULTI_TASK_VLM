# Contributing

## Workflow

1. Start from an up-to-date `main` branch.
2. Create a focused branch such as `feature/short-description`, `fix/short-description`, or `docs/short-description`.
3. Make and test a small, coherent change.
4. Commit with a concise message, then push the branch to GitHub.
5. Open a pull request (PR) into `main`, request review, and address feedback.
6. Merge only after approval and required checks pass.

## Commit messages

Use a short, imperative summary with a category, for example:

```text
feat: add night-domain evaluation
fix: handle empty sensor packets
docs: clarify dataset protocol
```

## Data and results

Do not commit raw datasets, extracted files, secrets, or generated intermediate outputs. Commit only curated, thesis-relevant result summaries and final artifacts when they are small enough for Git.
