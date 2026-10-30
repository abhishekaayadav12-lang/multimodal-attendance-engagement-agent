def fuse(visual, audio):
    """Fuse visual and acoustic activity using a transparent heuristic."""
    vmap = {int(x["window_start"]): float(x["visual_activity"]) for x in visual}
    amap = {int(x["window_start"]): float(x["audio_activity"]) for x in audio}

    windows = sorted(set(vmap) | set(amap))
    rows = []

    for start in windows:
        va = vmap.get(start)
        aa = amap.get(start)

        if va is not None and aa is not None:
            score = (0.45 * va + 0.55 * aa) * 100
        elif va is not None:
            score = va * 100
        else:
            score = aa * 100

        if score < 30:
            level = "Low"
        elif score < 60:
            level = "Medium"
        else:
            level = "High"

        rows.append(
            {
                "window_start": start,
                "visual_activity": None if va is None else round(va, 3),
                "audio_activity": None if aa is None else round(aa, 3),
                "engagement_score": round(score, 1),
                "level": level,
                "explanation": (
                    "Heuristic activity proxy from motion and acoustic energy; "
                    "not a measure of learning, attention, or emotion."
                ),
            }
        )

    return rows


def suggestions(rows):
    if not rows:
        return ["Run video and/or audio analysis first."]

    avg = sum(float(r["engagement_score"]) for r in rows) / len(rows)
    low_windows = [
        int(r["window_start"]) for r in rows if float(r["engagement_score"]) < 30
    ]

    if avg < 30:
        first = "Activity proxy is low; consider a recap, short break, or interactive activity."
    elif avg < 60:
        first = "Activity proxy is moderate; try a quick question, poll, or pair discussion."
    else:
        first = "Activity proxy is relatively high; maintain the current pace and check understanding."

    suggestions_list = [first]

    if low_windows:
        preview = ", ".join(f"{x}s" for x in low_windows[:5])
        suggestions_list.append(
            f"Review low-activity windows around: {preview}."
        )

    suggestions_list.append(
        "Validate the indicators with instructor observation and learner feedback."
    )
    return suggestions_list
