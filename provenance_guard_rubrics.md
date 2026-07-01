# Project 4: Provenance Guard

**Total Points:** 25 pts + 4 pts bonus

---

## Required Features

### Content Submission Endpoint (3 pts)
- Demo or source shows a text submission to the API returning a structured JSON response.
- The response includes an attribution result and a confidence score.
- The response includes transparency label text (not just a raw score).

### Multi-Signal Detection Pipeline (2 pts)
- README names 2 or more detection signals and explains what each captures and misses.
- Demo or source shows results reflecting both signals.

### Confidence Scoring with Uncertainty (2 pts)
- Demo shows at least two submissions with different confidence scores.
- README explains how signals are combined and validated.

### Transparency Label (3 pts)
- README includes the label text explicitly.
- Label uses plain language.
- Label differs between high and low confidence results.

### Appeals Workflow (2 pts)
- Demo shows an appeal submission with reasoning.
- Demo shows status updated to "under review" and logged.

### Rate Limiting (2 pts)
- Demo shows rate limiting behavior (e.g., 429 response).
- README explains limits and reasoning.

### Audit Log (3 pts)
- Demo shows at least 3 log entries with attribution, score, timestamp.
- Log is structured (JSON/table/log file).
- Includes at least one appeal.

### planning.md (4 pts)
- Detection signals explained and combined.
- Uncertainty thresholds defined.
- Transparency label variants written out.
- Appeals workflow + edge cases + AI Tool Plan included.

### README (2 pts)
- Includes known limitations tied to signals.
- Includes reflection on implementation vs plan.

### AI Usage (2 pts)
- Describes at least 2 uses of AI tools.
- Explains what was revised or changed.

---

## Stretch Features

### Ensemble Detection (+1 pt)
- 3+ signals with weighting or voting strategy.

### Provenance Certificate (+1 pt)
- Certificate design and verification described.

### Analytics Dashboard (+1 pt)
- Shows at least 3 metrics (e.g., detection ratio, appeal rate).

### Multi-Modal Support (+1 pt)
- Processes non-text content and explains signals used.
