<!-- audit-log sample, rate-limit configuration and chosen limits, label variants, and appeal handling
-->
# Provenance Guide - planning.md
--- 
## Community 

**What community was chosen?**

**Why is this community a good fit for a classification task — what makes the discourse varied enough to be interesting?**

## Transparency label
<!--  Design and implement the label that would be displayed to a reader on the platform. It must communicate the attribution result in plain language and make the confidence level meaningful to a non-technical reader. Include a typed description of all three label variants (high-confidence AI, high-confidence human, uncertain) in your README — write out the exact text each one displays-->

**high-confidence AI**

**high-confidence human**

**uncertain**

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
---

## Confidence Scoring with Uncertainty 
<!-- explain how you approached this and how you tested whether your scores are meaningful.
 Your system must return a confidence score, not just a binary label. The score should reflect genuine uncertainty — a 0.51 confidence should produce a meaningfully different transparency label than a 0.95. Your README must explain how you approached this and how you tested whether your scores are meaningful.-->

--- 

## Rate limiting 
<!--  Implement rate limiting on your submission endpoint. Your README must document the limits you chose and your reasoning for those specific values. -->

---

## Architecture
<!-- -->


--- 

## AI Tool Plan

**Label stress-testing:** 

<!-- Give the AI your label definitions and edge case description, and ask it to generate 5–10 posts that sit at the boundary between two labels. If it produces posts you can't classify cleanly, your definitions need tightening — do that now, before you annotate 200 examples. -->
Provided AI label definitions of people, objects, systems, and ideas along with edge case descriptions. Instructed to generate 5-10 posts that sit at the boundary between two labels. The results did not show case a clean classification. The definitions had to b tightened to remove ambiguity.  
Provided Claude Code with the list of wrong predictions from the test set. Asked it to identify patterns across misclassified examples. The AI identified the noun-anchoring pattern (classifying based on the subject word rather than the nature of the critique), which was then verified manually against the confusion matrix.


**Annotation assistance:** 
 <!--Decide whether you'll use an LLM to pre-label a batch of examples before reviewing them yourself. If yes, note which tool you'll use and how you'll track which examples were pre-labeled (for disclosure in your AI usage section).-->
Will review labels for examples without the aid of an annotation assistance. 

 **Failure analysis:**
 <!--Plan to give your list of wrong predictions to an AI tool and ask it to identify patterns before you write up your evaluation. Note what you'll look for and how you'll verify the patterns yourself. --> 
Will provide a list of wrong predictions to the AI tool and look confidence scores and will verify the pattern by reviewing the fine-tuned model set.

---


