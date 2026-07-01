<!-- Goals: Design and implement a multi-signal AI content classification pipeline.
Build confidence scoring that communicates uncertainty rather than forcing binary outputs.
Create end-user transparency labels that surface AI verdicts clearly and fairly.
Implement an appeals workflow for contested classifications.
Add production safety infrastructure: rate limiting and structured audit logging. -->

<!--LLM-based classification (Groq): ask the model to assess whether text reads as human or AI-generated. Captures semantic and stylistic coherence holistically.-->
<!--Stylometric heuristics: measurable statistical properties that differ between human and AI writing — sentence length variance, type-token ratio (vocabulary diversity), punctuation density, or average sentence complexity. AI text tends to be more uniform; human writing is more variable. Computable in pure Python. -->
# Provenance Guide - planning.md
--- 
## Community 

**What community was chosen?**

**Why is this community a good fit for a classification task — what makes the discourse varied enough to be interesting?**

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
<!--Incorporate 3 or more detection signals with a documented weighting or voting approach.-->


**Provenance certificate**
<!-- Design and implement a "verified human" credential that a creator can earn through an additional verification step, including how it's displayed on their content.-->


**Analytics dashboard**
<!--  Build a simple view showing detection patterns, appeal rates, and one additional metric of your choosing.-->


**Multi-modal support**
<!--Extend the pipeline to handle a second content type (e.g., image descriptions or structured metadata) in addition to text. -->


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
    - appeal recieved
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

---

## Audit log

<!-- Every attribution decision — including confidence score, signals used, and any appeals — must be captured in a structured audit log. Document the log in your README (or via the GET /log output) with at least 3 entries visible.-->

## Architecture


       SUBMISSION FLOW
+-------------------+
|   POST /submit    |
+-------------------+
          |
          |  raw text
          v
+-------------------+
|     signal 1      |
+-------------------+
          |
          |  signal score
          v
+-------------------+
|     signal 2      |
+-------------------+
          |
          |  signal score
          v
+---------------------------+
|   confidence scoring      |
+---------------------------+
          |
          |  combined score
          v
+---------------------------+
|   transparency label      |
+---------------------------+
          |
          |  label text
          v
+-------------------+
|     audit log     |
+-------------------+
          |
          |  labeled result
          v
+-------------------+
|      response     |
+-------------------+
          |
          |  response + label
          v
     (optional appeal)
          |
          v

                           APPEAL FLOW
+-------------------+
|   POST /appeal    |
+-------------------+
          |
          |  appeal text / case ID
          v
+---------------------------+
|      status update        |
+---------------------------+
          |
          |  updated status
          v
+-------------------+
|     audit log     |
+-------------------+
          |
          |  updated record
          v
+-------------------+
|      response     |
+-------------------+


Submission for text is first submitted, then taking to the signal 1 to check if it reads as human or AI, capturing sematic and stylistic coherence holistically, and provided a score. It then taken to signal 2 to check for statistical properties that differ between human and AI writing and provided a score. The text will be then provided a confidence score for transparency labels. It will then got to audit log to label results. The last step is for response and label.


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




**Annotation assistance:** 
 <!--Decide whether you'll use an LLM to pre-label a batch of examples before reviewing them yourself. If yes, note which tool you'll use and how you'll track which examples were pre-labeled (for disclosure in your AI usage section).-->
Will review labels for examples without the aid of an annotation assistance. 

 **Failure analysis:**
 <!--Plan to give your list of wrong predictions to an AI tool and ask it to identify patterns before you write up your evaluation. Note what you'll look for and how you'll verify the patterns yourself. --> 
Will provide a list of wrong predictions to the AI tool and look confidence scores and will verify the pattern by reviewing the fine-tuned model set.

---
