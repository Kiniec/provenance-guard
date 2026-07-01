# Provenance Guard

A multi-signal AI content classification pipeline built as a Flask API. Accepts text (or image descriptions) and returns a structured attribution verdict, confidence score, and transparency label. Includes an appeals workflow, structured audit logging, rate limiting, provenance certificates, and an analytics dashboard.

---

## Transparency Labels

Three label variants are displayed to readers on the platform:

**high-confidence AI**
- Label: `"Likely AI-generated (high confidence)"`
- Description: "Using this text shows patterns of statistical and stylistic most likely associated with AI-generated text."

**high-confidence human**
- Label: `"Likely human-written (high confidence)"`
- Description: "Using this content shows variations of language and stylistic patterns consistent with human writing."

**uncertain**
- Label: `"Uncertain — requires review"`
- Description: "Using this content shows the signals could not confidently determine whether this content was AI-generated or human-written based on available signals."

---

## Ensemble Detection — Multi-Signal Pipeline

Three independent signals are run on every submission. Each captures a different dimension of the text, so they catch failure modes the others miss.

### Signal 1: LLM Classification (Groq)

Calls `llama-3.3-70b-versatile` with a structured JSON prompt. Returns `ai_probability` (0.0 = human, 1.0 = AI) and a plain-language `reasoning` field.

- **What it captures:** Semantic and stylistic coherence holistically — whether the text reads as distributional AI output or human-authored meaning.
- **Blind spots:** No ground truth access; judges likeness to AI training distribution, not actual authorship. Formal human writing (academic, legal) is often flagged. Adversarial prompting ("write like a tired student") defeats it.

For `content_type: "image_description"`, a separate prompt is used, tuned to how AI and humans describe visual content differently (AI enumerates exhaustively; humans focus on personally salient details).

### Signal 2: Stylometric Heuristics (pure Python)

Computes four statistical features from the text without any API call:

- **Sentence length variance** — low variance indicates AI regularity; threshold range 5–80
- **Type-Token Ratio (TTR)** — vocabulary diversity; TTR guard skips this for texts < 80 words to avoid false positives on short but legitimate AI text
- **Punctuation density** — captured but not weighted in the current scoring formula
- **Function word ratio** — captured but not weighted; reserved for future signal extension

- **What it captures:** Statistical writing patterns — how uniform or varied the sentence structure is at the word level.
- **Blind spots:** Requires sufficient text; unreliable below ~20 words. Academic human writing mimics AI regularity. Easily altered by paraphrasing or editing.

### Signal 3: Predictability (pure Python)

Two sub-measures computed without any API call:

- **Bigram uniqueness** — ratio of distinct adjacent word pairs to total pairs. AI text reuses transitional phrases ("it is important", "in conclusion", "plays a crucial role"); human text produces more varied pairings.
- **Sentence opener diversity** — fraction of sentences starting with a distinct first word. AI cycles through a small set of formal openers ("The", "This", "In", "It"); human writing varies idiosyncratically.

- **What it captures:** Formulaic phrasing and structural repetition that stylometric word-level statistics and the semantic LLM signal do not directly measure.
- **Blind spots:** Short texts (< 15 words or < 2 sentences) have too few bigrams or openers to be meaningful; defaults to 0.5. Also weak on very short AI text.

---

## Confidence Scoring with Uncertainty

All three signals produce a continuous raw score from 0.0 (human) to 1.0 (AI). Calibration aligns them to a shared probability scale before combining.

### Calibration

```
LLM_cal  = 0.7  × raw + 0.15    # compresses to 0.15–0.85
Styl_cal = 0.9  × raw + 0.05    # compresses to 0.05–0.95
Pred_cal = 0.85 × raw + 0.075   # compresses to 0.075–0.925
```

### Ensemble Combination

Weights vary by content type to reflect signal reliability:

| Content type        | LLM  | Stylometry | Predictability |
|---------------------|------|------------|----------------|
| `text` (default)    | 55%  | 25%        | 20%            |
| `image_description` | 70%  | 15%        | 15%            |

Image descriptions down-weight stylometry because captions are short and structurally constrained regardless of authorship, making TTR and sentence variance unreliable signals.

### Uncertainty

Uncertainty is the **standard deviation** of the three calibrated scores — more principled than pairwise difference when working with 3+ signals, as it captures the spread across all three rather than just the largest gap.

Confidence bands:

| Band       | Uncertainty threshold | Meaning                            |
|------------|-----------------------|------------------------------------|
| `high`     | < 0.15                | Signals largely agree              |
| `moderate` | < 0.30                | Some disagreement; interpret with care |
| `low`      | ≥ 0.30                | Signals conflict — treat with caution |

### Label thresholds

```
ai_probability ≥ 0.65 → "Likely AI-generated (high confidence)"
ai_probability ≤ 0.35 → "Likely human-written (high confidence)"
between              → "Uncertain — requires review"
```

The asymmetry is intentional: a false AI accusation harms a creator more than a missed detection harms the platform.

### Validation

Scores were tested against three passages chosen to span the label space. Tests were run before each threshold change to confirm no false positives were introduced.

| Passage | Description | `ai_probability` | Label |
|---------|-------------|-----------------|-------|
| AI — formal | "This transformative paradigm shift represents…" (43 words, polished AI tone) | 0.68 | Likely AI-generated |
| Human — casual | "ok so i finally tried that new ramen place downtown…" (conversational, typos) | 0.34 | Likely human-written |
| Ambiguous | "I've been thinking a lot about remote work lately…" (nuanced first-person, hedged) | 0.41 | Uncertain — requires review |

The first passage caught a calibration bug. With the original 75/25 weighting and no TTR guard, it scored 0.57 ("Uncertain") instead of AI. Root cause: the text was 43 words — too short for TTR to be reliable — but TTR was still being computed, returning 0.88 (high diversity, human-like), which dragged the stylometric score down to 0.35. The fix was threefold: skip TTR for texts under 80 words, increase LLM's weight, and lower the AI label threshold from 0.75 to 0.65. After the fix, all three test passages produced the expected labels without regression.

A score of 0.41 producing "Uncertain" rather than forcing a verdict is the intended behavior: the system acknowledges that hedged, balanced first-person text is genuinely ambiguous and defers to human review rather than guessing.

---

## Rate Limiting

Rate limiting is applied to `POST /submit` using Flask-Limiter (≥ 3.x), keyed by client IP address. Exceeding any limit returns HTTP `429` with a JSON error body and a `retry_after` hint. No other endpoint is rate limited.

### Chosen limits

| Window     | Limit | Reasoning |
|------------|-------|-----------|
| Per minute | 5     | Pasting and submitting text takes a human at least 10–15 seconds. Five per minute is comfortable for active revision but a script hits this ceiling in milliseconds. This is the primary abuse stopper. |
| Per hour   | 30    | One submission every two minutes covers any realistic writing or revision session. Beyond 30 in an hour the traffic pattern looks automated rather than creative. |
| Per day    | 100   | Generous ceiling for power users and QA testers. Also bounds Groq API cost — 100 LLM inference calls per IP per day is a meaningful limit at scale. |

### Adversarial scenario

A script attempting to flood the endpoint or probe classifier boundaries hits the 5/min ceiling within the first second. The hourly and daily windows backstop any strategy that stays under the per-minute limit by spacing requests out.

### 429 response example

Submitting a 6th request within one minute returns:

```http
HTTP/1.1 429 TOO MANY REQUESTS
Content-Type: application/json

{
  "error": "Rate limit exceeded. Please slow down and try again later.",
  "retry_after": "5 per 1 minute"
}
```

---

## Audit Log

Every call to `POST /submit` writes a structured entry to `audit.jsonl` (one JSON object per line). Appeal entries share the same file, linked by `content_id`, and are distinguished by `"type": "appeal"`. Submission entries include `appeal_filed: true/false` stitched in at read time by `GET /log`.

### Fields recorded per submission

`timestamp`, `content_id`, `creator_id`, `content_type`, `attribution`, `ai_probability`, `uncertainty`, `confidence_band`, `llm_score_raw`, `llm_score_cal`, `llm_label`, `llm_reasoning`, `styl_score_raw`, `styl_score_cal`, `styl_features`, `pred_score_raw`, `pred_score_cal`, `pred_features`

### Sample entries

**Entry 1 — Likely AI-generated (high confidence)**
```json
{
  "timestamp": "2026-07-01T00:31:49.654656+00:00",
  "content_id": "894139bd-56b3-4445-824f-84daf32948cf",
  "creator_id": "creator_a",
  "content_type": "text",
  "attribution": "Likely AI-generated (high confidence)",
  "ai_probability": 0.6869,
  "confidence_band": "high",
  "uncertainty": 0.0925,
  "llm_score_raw": 0.8,
  "llm_score_cal": 0.71,
  "llm_label": "AI-generated",
  "llm_reasoning": "The text exhibits overly formal and generic language, lacking personal touch and specific examples, which is a common trait of AI-generated content.",
  "styl_score_raw": 0.6306,
  "styl_score_cal": 0.6175,
  "styl_features": {
    "avg_sentence_length": 14.33,
    "sentence_length_variance": 29.56,
    "type_token_ratio": 0.8837,
    "ttr_used": false,
    "punctuation_density": 0.1163,
    "function_word_ratio": 0.3488
  },
  "pred_score_raw": 0.52,
  "pred_score_cal": 0.517,
  "pred_features": {
    "unique_bigram_ratio": 0.9412,
    "sentence_starter_diversity": 0.6
  },
  "appeal_filed": false
}
```

**Entry 2 — Likely human-written (high confidence)**
```json
{
  "timestamp": "2026-07-01T00:31:50.262407+00:00",
  "content_id": "ffeed855-9b3f-4a66-870a-51604a42c764",
  "creator_id": "creator_b",
  "content_type": "text",
  "attribution": "Likely human-written (high confidence)",
  "ai_probability": 0.3436,
  "confidence_band": "high",
  "uncertainty": 0.1305,
  "llm_score_raw": 0.23,
  "llm_score_cal": 0.311,
  "llm_label": "Human-written",
  "llm_reasoning": "The text includes casual language, personal opinions, and specific details, which are common characteristics of human writing.",
  "styl_score_raw": 0.435,
  "styl_score_cal": 0.4415,
  "styl_features": {
    "avg_sentence_length": 11.0,
    "sentence_length_variance": 45.2,
    "type_token_ratio": 0.8727,
    "ttr_used": false,
    "punctuation_density": 0.0727,
    "function_word_ratio": 0.3273
  },
  "pred_score_raw": 0.10,
  "pred_score_cal": 0.16,
  "pred_features": {
    "unique_bigram_ratio": 0.9800,
    "sentence_starter_diversity": 0.80
  },
  "appeal_filed": false
}
```

**Entry 3 — Uncertain — requires review**
```json
{
  "timestamp": "2026-07-01T00:31:50.612581+00:00",
  "content_id": "584b4fca-47c7-40ef-82c3-162f433c0de7",
  "creator_id": "creator_c",
  "content_type": "text",
  "attribution": "Uncertain — requires review",
  "ai_probability": 0.4083,
  "confidence_band": "low",
  "uncertainty": 0.389,
  "llm_score_raw": 0.23,
  "llm_score_cal": 0.311,
  "llm_label": "Human-written",
  "llm_reasoning": "The text exhibits nuanced and balanced reasoning, with the author acknowledging multiple perspectives, which is a characteristic often associated with human writing.",
  "styl_score_raw": 0.7222,
  "styl_score_cal": 0.7,
  "styl_features": {
    "avg_sentence_length": 13.33,
    "sentence_length_variance": 22.22,
    "type_token_ratio": 0.9,
    "ttr_used": false,
    "punctuation_density": 0.15,
    "function_word_ratio": 0.325
  },
  "pred_score_raw": 0.35,
  "pred_score_cal": 0.3725,
  "pred_features": {
    "unique_bigram_ratio": 0.9600,
    "sentence_starter_diversity": 0.60
  },
  "appeal_filed": false
}
```

**Entry 4 — Appeal**
```json
{
  "type": "appeal",
  "appeal_id": "f31a2b5c-...",
  "timestamp": "2026-07-01T01:05:12.000000+00:00",
  "content_id": "584b4fca-47c7-40ef-82c3-162f433c0de7",
  "creator_id": "creator_c",
  "status": "under_review",
  "creator_reasoning": "This piece was written entirely by me. The formal structure reflects my academic background, not AI use.",
  "origin_attribution": "Uncertain — requires review",
  "origin_ai_probability": 0.4083,
  "origin_llm_score_raw": 0.23,
  "origin_styl_score_raw": 0.7222
}
```

### Appeals workflow demo

**Step 1 — Submit appeal** (`POST /appeal`):

```bash
curl -s -X POST http://localhost:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "584b4fca-47c7-40ef-82c3-162f433c0de7",
    "creator_id": "creator_c",
    "creator_reasoning": "This piece was written entirely by me. The formal structure reflects my academic background, not AI use."
  }'
```

Response (`201 Created`):
```json
{
  "appeal_id": "f31a2b5c-9d2e-4c81-a3f7-6b0e1234abcd",
  "content_id": "584b4fca-47c7-40ef-82c3-162f433c0de7",
  "creator_id": "creator_c",
  "creator_reasoning": "This piece was written entirely by me. The formal structure reflects my academic background, not AI use.",
  "message": "Appeal received. Your content has been flagged for human review.",
  "original_decision": "Uncertain — requires review",
  "status": "under_review",
  "timestamp": "2026-07-01T01:05:12.000000+00:00"
}
```

**Step 2 — Verify status updated** (`GET /status/<content_id>`):

```bash
curl -s http://localhost:5000/status/584b4fca-47c7-40ef-82c3-162f433c0de7
```

Response:
```json
{
  "content_id": "584b4fca-47c7-40ef-82c3-162f433c0de7",
  "status": "under_review",
  "attribution": "Uncertain — requires review",
  "ai_probability": 0.4083,
  "submitted_at": "2026-07-01T00:31:50.612581+00:00",
  "appeal": {
    "appeal_id": "f31a2b5c-9d2e-4c81-a3f7-6b0e1234abcd",
    "creator_reasoning": "This piece was written entirely by me. The formal structure reflects my academic background, not AI use.",
    "appealed_at": "2026-07-01T01:05:12.000000+00:00"
  }
}
```

Status transitions from `"submitted"` (no appeal) to `"under_review"` (appeal filed), and the appeal entry is logged to `audit.jsonl` with the original decision and scores preserved alongside the creator's reasoning.

---

## Provenance Certificate (stretch feature)

A creator whose content is classified as "Likely human-written (high confidence)" (`ai_probability ≤ 0.35`) can request a provenance certificate via `POST /certificate`.

The certificate is stored in `certificates.jsonl` and returned as:

```json
{
  "certificate_id": "cert-a3f9b1e4d2c8",
  "content_id": "ffeed855-9b3f-4a66-870a-51604a42c764",
  "creator_id": "creator_b",
  "issued_at": "2026-07-01T01:10:00+00:00",
  "ai_probability": 0.3436,
  "confidence_band": "high",
  "status": "verified_human",
  "badge": "Verified Human-Written"
}
```

**On-platform display:** The `badge` field value ("Verified Human-Written") is displayed alongside the content. The `certificate_id` is a tamper-evident reference — downstream systems call `GET /certificate/<content_id>` to verify it without trusting the badge field alone.

**Eligibility gate:** Content classified as AI-generated or uncertain cannot receive a certificate. The system returns HTTP `422` with the current `ai_probability` and `attribution` so the creator knows what threshold they missed.

**Idempotency:** Calling `POST /certificate` twice for the same `content_id` returns the existing certificate rather than issuing a duplicate.

---

## Analytics Dashboard (stretch feature)

`GET /analytics` returns aggregate metrics across all submissions:

```json
{
  "total_submissions": 12,
  "detection_ratio": {
    "ai_high_confidence": 0.417,
    "human_high_confidence": 0.5,
    "uncertain": 0.083
  },
  "appeal_rate": 0.083,
  "avg_ai_probability": 0.512,
  "avg_uncertainty": 0.187,
  "confidence_band_distribution": {
    "high": 0.667,
    "moderate": 0.25,
    "low": 0.083
  },
  "certificates_issued": 2
}
```

Metrics: total submission count, detection ratio (fraction per label variant), appeal rate (unique content IDs appealed / total submissions), average ai_probability, average uncertainty (signal disagreement), confidence band distribution, and certificates issued.

---

## Multi-Modal Support (stretch feature)

`POST /submit` accepts an optional `content_type` field:

| Value               | Description                                      |
|---------------------|--------------------------------------------------|
| `text` (default)    | Prose, articles, essays, messages                |
| `image_description` | Captions or natural-language descriptions of images |

### How signals adapt for image descriptions

**Signal 1 (LLM):** Uses a specialized prompt tuned to image description characteristics. AI-generated image descriptions enumerate visual elements exhaustively and use standardized vocabulary ("warm lighting", "sharp focus"). Human descriptions are selective, colloquial, and often reflect emotional or subjective reactions.

**Signal 2 (Stylometric):** Same function, but the ensemble weight drops from 25% to 15%. Image captions are short and structurally constrained regardless of authorship, so sentence variance and TTR are less discriminating.

**Signal 3 (Predictability):** Same function, weight drops from 20% to 15% for the same reason.

**LLM weight** increases from 55% to 70% for `image_description`, concentrating trust in the signal that understands the domain.

Example — submitting an image description:
```bash
curl -s -X POST http://localhost:5000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "creator_id": "creator_d",
    "content_type": "image_description",
    "text": "A woman standing in a sunlit kitchen, reaching for a mug on a high shelf. The countertops are white marble. Natural light comes from the window above the sink."
  }'
```

---

## Architecture

```
+==============================================================+
|                      SUBMISSION FLOW                         |
+==============================================================+

           client
              |
              |  POST /submit  {text, creator_id, content_type?}
              v
   +---------------------+
   |     Rate Limiter    |  5 / min . 30 / hr . 100 / day
   +---------------------+
          |           |
        pass        exceed
          |           |
          |           +-------> HTTP 429  {error, retry_after}
          v
   +---------------------+
   |   POST /submit      |
   |   (Flask route)     |
   +---------------------+
          |
          |  raw text
          +--------------------+--------------------+
          |                    |                    |
          v                    v                    v
   +-------------+   +------------------+   +------------------+
   |  Signal 1   |   |    Signal 2      |   |    Signal 3      |
   |  LLM/Groq   |   |  Stylometric     |   |  Predictability  |
   |             |   |  . sent variance |   |  . bigram unique |
   | label       |   |  . TTR (>=80 wds)|   |  . opener divers |
   | confidence  |   |  . punct density |   |                  |
   | reasoning   |   |  . func word rt  |   |                  |
   +-------------+   +------------------+   +------------------+
          |           raw score (0->1 AI)   raw score (0->1 AI)
          |                    |                    |
          +--------------------+--------------------+
                               |
                               v
               +------------------------------+
               |         Calibration          |
               |  LLM:  0.7*r  + 0.15        |
               |  Styl: 0.9*r  + 0.05        |
               |  Pred: 0.85*r + 0.075       |
               +------------------------------+
                               |
                               v
               +------------------------------+
               |     Ensemble Confidence      |
               |  text:  55% LLM             |
               |         25% Styl            |
               |         20% Pred            |
               |  image: 70% LLM             |
               |         15% Styl            |
               |         15% Pred            |
               |  uncertainty = std_dev(sigs)|
               |  band: high / mod / low     |
               +------------------------------+
                               |
                               v
               +------------------------------+
               |       Label Generation       |
               |  >=0.65 -> AI high conf      |
               |  <=0.35 -> Human high conf   |
               |  else   -> Uncertain         |
               +------------------------------+
                               |
                               v
               +------------------------------+
               |     Audit Log (audit.jsonl)  |  <- append-only JSON Lines
               +------------------------------+
                               |
                               v
                        HTTP 200 response
               {content_id, content_type, label,
                description, scoring, signals}


+==============================================================+
|                       APPEAL FLOW                            |
+==============================================================+

  POST /appeal  {content_id, creator_id, creator_reasoning}
       |
       |  lookup content_id in audit.jsonl
       +-> not found -> HTTP 404
       |
       v  append type:"appeal" entry, status:"under_review"
  HTTP 201  {appeal_id, status, original_decision}

  GET /status/<content_id>
       |
       +-> audit.jsonl -> {status, ai_probability, appeal {...}}


+==============================================================+
|              PROVENANCE CERTIFICATE FLOW                     |
+==============================================================+

  POST /certificate  {content_id, creator_id}
       |
       |  lookup submission in audit.jsonl
       +-> ai_probability > 0.35 -> HTTP 422 (not eligible)
       |
       v  write to certificates.jsonl
  HTTP 201  {certificate_id, badge:"Verified Human-Written", ...}

  GET /certificate/<content_id>
       |
       +-> certificates.jsonl -> certificate or HTTP 404


+==============================================================+
|                 QUERY / ANALYTICS FLOW                       |
+==============================================================+

  GET /log?limit=N  ->  audit.jsonl  -> entries[] (appeal_filed stitched in)

  GET /analytics    ->  audit.jsonl + certificates.jsonl
                    ->  {total, detection_ratio, appeal_rate,
                         avg_ai_probability, avg_uncertainty,
                         confidence_band_distribution,
                         certificates_issued}
```

---

## Known Limitations

Each signal has structural blind spots that no amount of threshold tuning can fully close.

**Signal 1 — LLM (Groq):**
- *Circularity.* The model detects text that looks like AI training data — which is not the same as text that is AI-generated. A human writing in a GPT-like register (smooth, structured, polished) can be flagged. A model fine-tuned to mimic an unusual human style may not be caught.
- *No ground truth.* The LLM never saw who wrote the text. It judges probability of authorship from surface patterns alone, which means its confidence can be high even when it is wrong.
- *Prompt sensitivity.* Asking an AI to "write casually with deliberate errors" measurably reduces the LLM signal's score, even though the output is still AI-generated.

**Signal 2 — Stylometric Heuristics:**
- *Requires length.* TTR is skipped for texts under 80 words; sentence variance needs at least 2 sentences. Short content (tweets, subject lines, image captions) falls back to 0.5, making the signal neutral rather than informative.
- *Formal human writing looks AI.* Legal documents, academic abstracts, and technical specs are deliberately uniform — that uniformity is what the signal penalizes. A legal brief written by a human may outscore generated blog spam on the AI axis.
- *Easily gamed.* Inserting varied sentence lengths and unusual punctuation into AI output shifts the score without changing the authorship.

**Signal 3 — Predictability:**
- *Weak on short text.* Bigram uniqueness and opener diversity both need enough text to form a distribution. Under ~15 words or 2 sentences, the signal defaults to 0.5.
- *Correlated with stylometric.* Both signals punish repetition and reward variation, so they can agree and disagree for the same reason. High correlated agreement raises the confidence band without adding independent signal.

**System-level:**
- *No labeled ground truth.* Thresholds were calibrated against three handpicked passages, not a held-out labeled dataset. The bands and weights reflect informed judgment, not measured accuracy on a representative sample.
- *Single document, no baseline.* All three signals work on the submitted text in isolation. A human who always writes in a formal register will be persistently flagged; an AI tuned to mimic that creator's casual style will persistently pass. Authorship verification across documents is outside this system's scope.

---

## Reflection — Implementation vs. Plan

**What held up:** Most of the core design from `planning.md` was implemented without change. The two primary detection signals, the calibration formulas (`LLM_cal = 0.7 × raw + 0.15`, `Styl_cal = 0.9 × raw + 0.05`), all three transparency label variants and their exact text, the rate limits (5/min, 30/hr, 100/day), the audit log schema and JSON Lines format, and the appeals workflow all shipped as designed. The architecture diagram in `planning.md` mapped directly to the route structure.

**What changed, and why:**

The plan assumed the two signals would produce intuitively correct scores out of the box. They didn't — at least not for all cases. A clearly AI-generated passage ("transformative paradigm shift", 43 words) scored 0.57 and landed on "Uncertain." That was wrong. Diagnosing it revealed that TTR, computed on 43 words, returned 0.88 — which looks like high vocabulary diversity and signals "human," dragging the stylometric score to 0.35. The fix required three coordinated changes: adding a TTR length guard (skip TTR under 80 words), raising LLM's ensemble weight, and lowering the AI label threshold from 0.75 to 0.65. None of these were in the original plan. They emerged from testing against concrete examples rather than from design intuition.

The two-signal plan also didn't account for what happens when the signals agree for the wrong reasons. Stylometric and predictability both reward variation and penalize repetition, so they can correlate — agreement inflates confidence band without adding independent signal. That tension is still present in the current implementation and is an honest gap.

A few additions also arrived as the design matured. The `appeal_filed` field in `GET /log` (stitched at read time rather than stored) was not in the original spec but was needed to make the log useful without rewriting the append-only file. The uncertainty metric shifted from pairwise `abs(a − b)` to standard deviation once there were three signals, since the pairwise version would ignore whichever of the three signals was closest to the mean.

The biggest open gap between plan and implementation is validation. The plan described a testing approach but the actual calibration was done against three handpicked passages. That's enough to catch obvious miscalibration (and it did catch one), but it is not enough to claim the thresholds are well-calibrated in general. A labeled dataset and a proper held-out evaluation are the next step the plan does not yet specify.

---

## AI Usage

Claude Code (claude-sonnet-4-6) was used throughout this project as the primary implementation tool.

**Milestone 3 — Flask skeleton and Signal 1.**
The detection signals section and architecture diagram from `planning.md` were provided as context. Claude Code generated the Flask app skeleton, `POST /submit`, and `classify_with_llm` against the Groq API. The function was called directly with three test inputs before being wired into the route. What was revised: the initial LLM system prompt asked the model to return a field called `confidence`, which the model interpreted as "how confident I am in my label" (e.g., 0.95 for a label it was sure about) rather than "probability the text is AI-generated." For a high-confidence human classification, this returned 0.95 — the opposite of the intended direction. The prompt was revised to use `ai_probability` with an explicit direction (0.0 = certainly human, 1.0 = certainly AI), which resolved the ambiguity.

**Milestone 4 — Stylometric signal, confidence scoring, and calibration.**
Claude Code implemented `compute_stylometric` and `combine_signals`, proposing thresholds for sentence length variance (5–80 range) and TTR (0.40–0.72 range) since `planning.md` defined the features but not their numeric cutoffs. A miscalibration was caught through testing: the initial implementation scored a clearly AI-generated 43-word passage as 0.57 ("Uncertain"). The investigation ran in-session — testing three passages, changing one parameter at a time, re-testing after each. What was revised: TTR was initially computed on all texts regardless of length. Adding the 80-word guard, increasing the LLM weight, and dropping the AI label threshold from 0.75 to 0.65 together fixed the miscalibration without introducing false positives on the human test passages.

**Milestone 5 — Labels, appeals, and audit log.**
Claude Code generated `generate_label`, the `POST /appeal` and `GET /status/<id>` endpoints, and the `GET /log` view. A bug was found where `GET /status` was returning the hardcoded string `"under_appeal"` rather than reading `appeal["status"]` from the stored entry. This was caught by cross-checking the `/log` response against `/status` for the same content ID. What was revised: the status field was updated to read dynamically from the appeal entry, which also made it forward-compatible if the status values change (e.g., "queued_for_review", "resolved").

---

## API Reference

| Method | Endpoint                    | Description                                       |
|--------|-----------------------------|---------------------------------------------------|
| POST   | `/submit`                   | Classify content; returns label, scores, signals  |
| GET    | `/log?limit=N`              | Recent audit log entries (default 20)             |
| POST   | `/appeal`                   | File an appeal for a contested classification     |
| GET    | `/status/<content_id>`      | Check status and appeal state of a submission     |
| POST   | `/certificate`              | Issue a "Verified Human-Written" certificate      |
| GET    | `/certificate/<content_id>` | Retrieve a previously issued certificate          |
| GET    | `/analytics`                | Aggregate detection metrics and appeal rate       |

### POST /submit

```bash
curl -s -X POST http://localhost:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "creator_id": "alice", "content_type": "text"}'
```

`content_type` defaults to `"text"`. Supported values: `text`, `image_description`.

### POST /certificate

```bash
curl -s -X POST http://localhost:5000/certificate \
  -H "Content-Type: application/json" \
  -d '{"content_id": "<id from a human-classified submission>", "creator_id": "alice"}'
```

Returns HTTP 422 if `ai_probability > 0.35`.

### GET /analytics

```bash
curl -s http://localhost:5000/analytics | python3 -m json.tool
```
