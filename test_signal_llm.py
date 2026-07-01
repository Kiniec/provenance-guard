"""
Run independently to verify classify_with_llm before wiring into the endpoint.
  python test_signal_llm.py
"""
import json
from app import classify_with_llm

CASES = [
    (
        "clearly AI",
        (
            "Artificial intelligence is revolutionizing numerous industries by enabling "
            "machines to perform tasks that previously required human intelligence. "
            "Through the application of machine learning algorithms and neural networks, "
            "AI systems can now analyze vast datasets, recognize patterns, and make "
            "data-driven decisions with remarkable accuracy and efficiency."
        ),
    ),
    (
        "clearly human",
        (
            "ok so i was trying to explain this to my roommate last night and honestly "
            "i still don't get it lol. like the whole point is that the model learns from "
            "data?? but then how does it actually *know* anything. idk it just feels like "
            "magic to me. anyway she didn't care and we ended up watching tv instead"
        ),
    ),
    (
        "ambiguous",
        (
            "The experiment didn't go as planned. We expected a linear relationship "
            "between dosage and response, but the data showed something more complicated — "
            "a plateau around 40mg that none of us anticipated. Worth investigating further."
        ),
    ),
]

for name, text in CASES:
    print(f"\n{'='*60}")
    print(f"CASE: {name}")
    print(f"TEXT: {text[:80]}...")
    result = classify_with_llm(text)
    print(json.dumps(result, indent=2))
