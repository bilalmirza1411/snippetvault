def fuzzy_match(query: str, text: str, max_edits: int = 1):
    """Return the smallest edit distance between query and any substring
    of text, or None if that distance is greater than max_edits."""
    q, t = query.lower(), text.lower()
    m = len(q)
    if m == 0:
        return None

    # prev[i] = edit distance of q[:i] against the best substring ending
    # at the previous text position.
    prev = list(range(m + 1))
    best = prev[m]
    for ch in t:
        curr = [0] * (m + 1)          # row 0 stays 0: a match can start anywhere
        for i in range(1, m + 1):
            cost = 0 if q[i - 1] == ch else 1
            curr[i] = min(
                prev[i - 1] + cost,   # match or substitute
                prev[i] + 1,          # extra character in the text
                curr[i - 1] + 1,      # missing character in the text
            )
        best = min(best, curr[m])
        prev = curr

    return best if best <= max_edits else None