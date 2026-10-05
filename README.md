# PharmEasy Regional Pulse

## Install and run

Requires Python 3.11 or newer. From the repository root, run:

```bash
python -m pip install -r requirements.txt
python pipeline.py
python -m streamlit run app.py
```

The pipeline generates the dataset, cleans and validates it, builds SQLite metrics, and prepares the reports. Review the printed package and enter `approve`, `edit`, or `reject`, followed by your name and what you checked. Approval allows the dashboard to display the report. No paid services or API keys are required.

## Four-artifact cover note

Guntur sales increased **122.19% from April to May 2026**, from **₹62,442.27 to ₹138,738.93**, the largest-magnitude flagged transition in the dataset.

- **Streamlit dashboard (`app.py`):** live exploration of regional sales, profit, orders, and categories.
- **CII narrative (embedded in the dashboard):** Context–Insight–Implication explanations of flagged regional changes.
- **One-page memo (`memo.md`):** evidence and the recommendation for Guntur.
- **Presentation storyline (`presentation_storyline.md`):** audience-specific framing and responses to stakeholder questions.

Review order: **dashboard → embedded CII narrative → memo → presentation storyline**.

Unverified assumption from the memo: **Changes in order composition may explain the swing, but no causal explanation has been verified.** [MEDIUM]

## Output folder

Generated CSV data, the SQLite database, JSON state/report files, and the JSONL audit log are stored in `output/`. Python scripts and all Markdown files remain in the repository root. The files that were generated during testing in local system were placed in localOutputFiles folder in the project.
