"""
Verify compute_stylometric and combine_signals independently.
  python test_signal_stylometric.py
"""
import json
from app import compute_stylometric, combine_signals

CASES = [
    (
        "clearly AI — uniform, structured",
        (
            "Artificial intelligence is transforming the modern economy. "
            "Machine learning enables systems to improve from experience. "
            "Neural networks process information in layered architectures. "
            "Deep learning models require large volumes of training data. "
            "These systems achieve remarkable accuracy on complex tasks."
        ),
    ),
    (
        "clearly human — casual, varied",
        (
            "ok so i was trying to explain this to my roommate last night and honestly "
            "i still don't get it lol. like the whole point is that the model learns from "
            "data?? but then how does it actually *know* anything. idk. "
            "she didn't care and we ended up watching tv. anyway. "
            "i have a midterm on this tomorrow and i'm cooked."
        ),
    ),
    (
        "ambiguous — short scientific note",
        (
            "The experiment didn't go as planned. We expected a linear relationship "
            "between dosage and response, but the data showed a plateau around 40mg "
            "that none of us anticipated. Worth investigating."
        ),
    ),
    (
        "academic human — formal but human-authored",
        (
            "The results were, frankly, surprising. Prior literature suggested a monotonic "
            "increase — and yet here we are. Three replication attempts, same plateau. "
            "I want to be careful not to over-interpret this; the sample size is small "
            "and the effect could easily disappear with n=100. "
            "Still. It's hard to ignore."
        ),
    ),
]

print("=" * 65)
print("SIGNAL 2: STYLOMETRIC HEURISTICS")
print("=" * 65)

for name, text in CASES:
    result = compute_stylometric(text)
    print(f"\nCASE  : {name}")
    print(f"TEXT  : {text[:72].strip()}...")
    print(f"SCORE : {result['score']}  (0=human, 1=AI)")
    print(f"FEATS : {json.dumps(result['features'], indent=8)}")

print()
print("=" * 65)
print("CONFIDENCE SCORING — combine_signals(llm_raw, styl_raw)")
print("Verifying calibration + band thresholds")
print("=" * 65)

# Spot-check the calibration formulas from planning.md:
#   LLM_score_cal  = 0.7 * raw + 0.15
#   Styl_score_cal = 0.9 * raw + 0.05
SCORING_CASES = [
    ("both strongly AI",     0.90, 0.85),
    ("both strongly human",  0.08, 0.10),
    ("signals agree — mid",  0.50, 0.50),
    ("signals disagree",     0.85, 0.15),
    ("LLM uncertain, styl AI", 0.55, 0.80),
]

for label, llm, styl in SCORING_CASES:
    s = combine_signals(llm, styl)
    llm_cal  = round(0.7 * llm  + 0.15, 4)
    styl_cal = round(0.9 * styl + 0.05, 4)
    print(f"\n{label}")
    print(f"  llm_raw={llm}  styl_raw={styl}")
    print(f"  llm_cal={llm_cal}  styl_cal={styl_cal}  (planning.md formulas)")
    print(f"  → ai_probability={s['ai_probability']}  uncertainty={s['uncertainty']}  band={s['confidence_band']}")
