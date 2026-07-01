<!-- Goals: Design and implement a multi-signal AI content classification pipeline.
Build confidence scoring that communicates uncertainty rather than forcing binary outputs.
Create end-user transparency labels that surface AI verdicts clearly and fairly.
Implement an appeals workflow for contested classifications.
Add production safety infrastructure: rate limiting and structured audit logging. -->

<!--LLM-based classification (Groq): ask the model to assess whether text reads as human or AI-generated. Captures semantic and stylistic coherence holistically.-->
<!--Stylometric heuristics: measurable statistical properties that differ between human and AI writing — sentence length variance, type-token ratio (vocabulary diversity), punctuation density, or average sentence complexity. AI text tends to be more uniform; human writing is more variable. Computable in pure Python. -->
# Provenance Guide - planning.md


## Transparency label
<!--  Design and implement the label that would be displayed to a reader on the platform. It must communicate the attribution result in plain language and make the confidence level meaningful to a non-technical reader. Include a typed description of all three label variants (high-confidence AI, high-confidence human, uncertain) in your README — write out the exact text each one displays.
The system should acknowledge uncertainty honestly and give creators a path to appeal. That's the real engineering challenge here.-->

**high-confidence AI** 

- Label: "Likely AI-generated (high confidence)".
    - Using this text shows patterns of  statistical and stylistic most likely associated with AI-generated text.

**high-confidence human**

- Label: "Likely human-written (high confidence)".
    - Using this content shows variations of language and stylistic patterns 
consistent with human writing.

**uncertain**

- Label: "Uncertain — requires review"
    - Using this content shows the signals could not confidently determine whether this content was AI-generated or human-written based on available signals.

---

**Ensemble detection**

Three signals with documented weighting per content type:

| Signal                 | Method      | Captures                                       |
|------------------------|-------------|------------------------------------------------|
| LLM (Groq)             | API         | Semantic/stylistic alignment with AI patterns  |
| Stylometric Heuristics | Pure Python | Word-level statistics (variance, TTR, punctuation) |
| Predictability         | Pure Python | Phrase-level repetition and opener diversity   |

Weights for `text`: 55% LLM, 25% Stylometry, 20% Predictability.
Weights for `image_description`: 70% LLM, 15% Stylometry, 15% Predictability.
Uncertainty = standard deviation of the three calibrated scores (more principled than pairwise diff for 3+ signals).

**Provenance certificate**

A "Verified Human-Written" credential issued via `POST /certificate`. Eligibility gate: `ai_probability ≤ 0.35` (high-confidence human classification). Stored in `certificates.jsonl`. The `badge` field ("Verified Human-Written") is displayed on-platform. The `certificate_id` is a tamper-evident reference — downstream systems call `GET /certificate/<content_id>` to verify without trusting the badge alone. Idempotent: re-requesting an existing certificate returns the original rather than issuing a duplicate.

**Analytics dashboard**

`GET /analytics` returns: total submissions, detection ratio (fraction per label variant), appeal rate, average ai_probability, average uncertainty, confidence band distribution, and certificates issued. Reads from `audit.jsonl` and `certificates.jsonl` at request time — no separate state.

**Multi-modal support**

`POST /submit` accepts `content_type: "text"` (default) or `content_type: "image_description"`. For image descriptions, Signal 1 uses a specialized prompt tuned to how AI and humans describe visual content differently. Signals 2 and 3 use the same functions with reduced weights because captions are short and structurally constrained regardless of authorship. Unsupported content types return HTTP 400.


--- 

## Multi-Signal Detection Pipeline
<!-- must explain what each signal captures and why you chose them.-->
Two signals that will be utilized will be LLM based-classification and Stylometric heuristics signal. 
- LLM- based-classification(Groq) will measure semantic judgement which includes measuring meaning plus style jointly and semantic plus contextual alignment with learned patterns. The output should be raw output text judgments.
Example: \
"This text is likely AI-generated because it is highly structured and consistent."  
>force structure \
{
  "label": "AI-generated",
  "confidence": 0.78,
  "reasoning": "high consistency, formal tone"
}
-  Stylometric heuristics signal will measure the style of writing such as encodes lexical, grammatical, punctuation, and syntactic patterns. The output should be raw features which is before some form of aggregation. 
Example: \
`Avg sentence length = 15.9, variance 2.1, function word ratio = .043` \



<**LLM based-classification**
semantic judgement 
- what property of the text is measures
    -  Semantic + contextual alignment with learned patterns
    - measures meaning + style jointly, not just surface or statistics
- why this differs between humans and AI writing
    - LLM - Often reflects training-distribution norms, Consistent structure (intro → body → conclusion)
    - Humans -  More situational, incomplete, or asymmetric,  abrupt endings, implicit assumptions, uneven reasoning
- exploits: 
    - AI → distributional conformity + polished reasoning patterns
    - Humans → context-dependent, sometimes messy reasoning

- blind spots: 
    - No ground truth access - judges likeness, not authorship
    - Model bias / circularity - It detects text similar to itself or its training data
    - Strong prompt sensitivity - Small phrasing changes → different classification
    - Overfits to “AI tone” - Formal human writing gets flagged
    - Adversarial prompting breaks it - “Write like a tired student with mistakes” → reduces signal
**Stylometric Heurstics Signal**
- what property of the text is measures
    - style of writing/ measures how a person writes
    - encodes lexical, grammatical, syntactic, and punctuation patterns 
- why this differs between humans and AI writing
    -  LLM more grammatically standardized , more uniform and consistent patterns. 
    - humans more - idiosyncratic variation, personal quirks(system rhythm, punctuation habits)
- exploits: 
    - AI -  low variance, high regularity
    - Humans -  higher stylistic entropy (variation)
- blind spots - 
    - Single-document weakness - works best relative to known writing samples
    - Easily altered - Editing, paraphrasing
    - style -  Two people (or models) can share similar style
    - fall short on text - Not enough signal for stable patterns
    -  Domain dependence - Academic writing (human) can look like AI- similar to uniform style 



---

## Confidence Scoring with Uncertainty 
<!-- explain how you approached this and how you tested whether your scores are meaningful. <!-- Your system must return a confidence score, not just a binary label. The score should reflect genuine uncertainty — a 0.51 confidence should produce a meaningfully different transparency label than a 0.95. Your README must explain how you approached this and how you tested whether your scores are meaningful.--> 

Both outputs have a type - continuous score, range - 0-1, meaning, for a final usable signal. \
- LLM 0 -> definitely human , 1 -> definitely AI \
- Stylometric heuristics signal -> 0, highly human , 1 -> highly AI regularity \

Calibration example: 

>LLM_score_cal = 0.7 * raw + 0.15 \
Styl_score_cal = 0.9 * raw + 0.05

The goal is to align both signals to same probability meaning to reduce overconfidence. 

**Combining into a single confidence score with uncertainty** \
Example: 
>{
  "ai_probability": 0.67,
  "uncertainty": 0.22,
  "confidence_band": "moderate",
  "signals": {
    "llm": 0.78,
    "stylometry": 0.81
  }
}

--- 

## Appeals Workflow
<!-- Implement a mechanism for creators to contest a classification. At minimum, an appeal must: capture the creator's reasoning, log the appeal alongside the original decision, and update the content's status to "under review." Automated re-classification is not required. -->

1. Any users of the system can submit an appeal for review of outputs. Examples are content creators, account owners, or as a reporter. The possible decisions that are appealable are content labels, content removable or restriction, account actions. \
2. The user would provide user identity, content reference, decision being appealed, decision date, and an user explanation of why the decision is in correct along with supporting evidence.
3. The system should move through clear states
    - "under_appeal"
    - "queued_for_review"
    - "in_review"
    - "resolved"
4. The audit trial of what is being logged is 
    - appeal received
    - who submitted it
    - timestamp
    - origin decision + scores
    - appeal reason text
    - action taken 
    - user 
    - content 
    - decision maker 
    

---

## Rate limiting 
<!--  Implement rate limiting on your submission endpoint. Your README must document the limits you chose and your reasoning for those specific values. 
Think about realistic usage on a writing platform: how often does a single creator submit work? How would an adversary try to flood the system? Document your reasoning. -->
Rate limiting would consist of  per minutes 5 , per hour 30, per day 100. 5 per minute, humans take about 10 texts for each word. It is good enough for revising. 30 per hour is good for ideal writing session. 100 per day is a ceiling is for users and quality assurance testers. These numbers were chosen due to the minute metric is crucial for automated probing and API exhausting. 100 per day is sufficient enough for power user, anything less could would block legitimate users. A script could try and attempt to flood or probed classifier boundaries. The numbers chosen stays under throttling request. 

---

## Audit log
<!-- Every attribution decision — including confidence score, signals used, and any appeals — must be captured in a structured audit log. Document the log in your README (or via the GET /log output) with at least 3 entries visible.-->
Every call to `POST /submit` writes a structured entry to `audit.jsonl` (one JSON object per line). Appeal entries share the same file, linked by `content_id`, and are distinguished by `"type": "appeal"`. Submission entries include `appeal_filed: true/false` stitched in at read time by `GET /log`.

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
          +----------------+----------------+
          |                |                |
          v                v                v
   +----------+   +--------------+   +--------------+
   | Signal 1 |   |  Signal 2    |   |  Signal 3    |
   | LLM/Groq |   | Stylometric  |   | Predictabil. |
   |          |   | . sent var   |   | . bigram uniq|
   | label    |   | . TTR>=80wds |   | . opener div |
   | ai_prob  |   | . punct dens |   |              |
   | reasoning|   | . func ratio |   |              |
   +----------+   +--------------+   +--------------+
        |          raw 0->1 AI          raw 0->1 AI
        |                |                    |
        +----------------+--------------------+
                         |
                         v
         +--------------------------------+
         |          Calibration           |
         |  LLM:  0.7*r  + 0.15          |
         |  Styl: 0.9*r  + 0.05          |
         |  Pred: 0.85*r + 0.075         |
         +--------------------------------+
                         |
                         v
         +--------------------------------+
         |      Ensemble Confidence       |
         |  text:  55% LLM               |
         |         25% Styl              |
         |         20% Pred              |
         |  image: 70% LLM               |
         |         15% Styl              |
         |         15% Pred              |
         |  uncertainty = std_dev(3 sigs)|
         |  band: high / mod / low       |
         +--------------------------------+
                         |
                         v
         +--------------------------------+
         |        Label Generation        |
         |  >=0.65 -> AI high conf        |
         |  <=0.35 -> Human high conf     |
         |  else   -> Uncertain           |
         +--------------------------------+
                         |
                         v
         +--------------------------------+
         |    Audit Log (audit.jsonl)     |  <- append-only JSON Lines
         +--------------------------------+
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
       v  append type:"appeal", status:"under_review"
  HTTP 201  {appeal_id, status, original_decision}

  GET /status/<content_id>
       |
       +-> audit.jsonl -> {status, ai_probability, appeal {...}}


+==============================================================+
|             PROVENANCE CERTIFICATE FLOW                      |
+==============================================================+

  POST /certificate  {content_id, creator_id}
       |
       |  lookup submission in audit.jsonl
       +-> ai_probability > 0.35 -> HTTP 422 (not eligible)
       +-> existing certificate -> return existing (idempotent)
       |
       v  append to certificates.jsonl
  HTTP 201  {certificate_id, badge:"Verified Human-Written", ...}

  GET /certificate/<content_id>
       +-> certificates.jsonl -> certificate or HTTP 404


+==============================================================+
|                QUERY / ANALYTICS FLOW                        |
+==============================================================+

  GET /log?limit=N  ->  audit.jsonl  -> entries[]
                         (appeal_filed stitched in at read time)

  GET /analytics    ->  audit.jsonl + certificates.jsonl
                    ->  {total, detection_ratio, appeal_rate,
                         avg_ai_probability, avg_uncertainty,
                         confidence_band_distribution,
                         certificates_issued}
```

Submission flow: text (or an image description) is submitted through a rate-limited endpoint and passed to all three detection signals. Signal 1 (LLM via Groq) captures semantic and stylistic coherence holistically, with a specialized prompt for image descriptions. Signal 2 (Stylometric Heuristics) measures word-level statistical properties — sentence length variance, type-token ratio, punctuation density, and function word ratio. Signal 3 (Predictability) measures phrase-level repetition (bigram uniqueness) and structural repetition (sentence opener diversity). All three raw scores are calibrated to a shared probability scale, then combined into a weighted ensemble confidence score with uncertainty derived from the standard deviation across all three calibrated scores. The confidence score drives label generation. Every decision is appended to audit.jsonl before the response is returned.

Appeal flow: a creator submits a content_id and their reasoning. The system looks up the original decision from the audit log, sets status to "under_review", appends an appeal entry alongside the original scores, and returns a confirmation.

Certificate flow: a creator whose content was classified as human (ai_probability ≤ 0.35) may request a "Verified Human-Written" provenance certificate. The certificate is stored in certificates.jsonl and returned with a badge field for on-platform display.

Query/analytics flow: GET /log returns all entries with appeal_filed stitched in at read time. GET /status returns the current state of a single submission. GET /analytics aggregates metrics across all submissions and certificates.


--- 

## AI Tool Plan

**Milestone 3**
<!--Which spec sections you'll provide to the AI tool (hint: your detection signals section + the diagram), what you'll ask it to generate (Flask app skeleton + the first signal function), and how you'll verify the output (test with a few inputs directly before wiring into the endpoint).-->
The sections that will be provided to Claude Code for implementation will be LLM- based-classification signal , Transparency labels, and the Architectural diagram of the system. Claude Code will be prompted to generate a Flask app skeleton along with the first signal function. The output will be tested with inputs directly wiring into the endpoint. 

**Milestone 4**
<!-- Which spec sections you'll provide (detection signals + uncertainty representation + diagram), what you'll ask for (second signal function + scoring logic), and what you'll 
check (do scores vary meaningfully between clearly AI and clearly human text?).-->
 The specifications provided to Claude code will be detection signals and confidence scoring with uncertainty. Claude Code will be asked to produce a Stylometric Heuristic signal function with scoring logic. Will check to verify if scores vary meaningfully between clearly AI and clearly human text.  

**Milestone 5**
<!--Which spec sections you'll provide (label variants + appeals workflow + diagram), what you'll ask for (label generation logic + the /appeal endpoint), and how you'll verify (test all three label variants are reachable and that an appeal updates status correctly).-->
Claude Code will be provided specs from the planning.md of transparency labels, appeals workflow and architectural design. Will ask for the output of label generation logic and the appeal endpoint. Test verification will be conducted so that all three label variants are reachable along with appeal updates status are correct. 


---
