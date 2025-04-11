import re

RED_FLAGS = {
    r"\bfraud(ulent|s|)\b": "high",
    r"\bunder investigation\b": "high",
    r"\bpending litigation\b": "medium",
    r"\bbreach of contract\b": "medium",
    r"\bterminated.*CEO\b": "low",
    r"\bbankrupt(cy|)\b": "high",
    r"\bSEC (notice|action)\b": "medium",
    r"\bsanction(ed)?\b": "medium",
    r"\bcriminal charge(s)?\b": "high",
    r"\bloss of customer data\b": "high"
}

def get_flagged_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    results = []

    for sent in sentences:
        for pattern, severity in RED_FLAGS.items():
            match = re.search(pattern, sent, re.IGNORECASE)
            if match:
                # Highlight the matched word in red and bold
                highlighted_sentence = re.sub(
                    pattern,
                    f"<strong style='color:#e74c3c;'>{match.group(0)}</strong>",
                    sent,
                    flags=re.IGNORECASE
                )
                results.append({
                    "sentence": highlighted_sentence.strip(),
                    "pattern": pattern,
                    "severity": severity
                })
    return results
