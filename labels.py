from signals import CONFIDENCE_THRESHOLD

# Display text from spec.md § Transparency Labels
_TEMPLATES = {
    "high_confidence_ai":    "Our AI detection system has determined this post to be AI-generated with a high confidence level ({score}%).",
    "high_confidence_human": "Our AI detection system has determined this post to be human-made with a high confidence level ({score}%).",
    "uncertain":             "Our AI detection system was unable to determine whether this post was AI-generated. Confidence level: {score}%.",
}


def generate_label(attribution: str, confidence_score: float) -> dict:
    """
    Map a confidence result to a display label.

    compute_confidence() already enforces the 0.75 threshold, so attribution
    is 'uncertain' exactly when confidence_score < CONFIDENCE_THRESHOLD.
    The mapping here is therefore a straight lookup on attribution.
    """
    if attribution == "ai":
        variant = "high_confidence_ai"
    elif attribution == "human":
        variant = "high_confidence_human"
    else:
        variant = "uncertain"

    score_pct = round(confidence_score * 100)
    return {
        "variant": variant,
        "display_text": _TEMPLATES[variant].format(score=score_pct),
    }
