def generate_coach_paragraph(analysis: dict) -> str:
    trend_data   = analysis.get("trend", {})
    trend        = trend_data.get("trend", "stable")
    overall_avg  = trend_data.get("overall_avg")
    best_period  = analysis.get("time_of_day", {}).get("best_period")
    best_len     = analysis.get("session_length", {}).get("best_length")
    top_dist     = analysis.get("distractions", {}).get("most_frequent")
    forecast     = analysis.get("ml_forecast", {})
    fi           = analysis.get("ml_feature_importance", {})
    dow          = analysis.get("day_of_week", {})
    best_day     = dow.get("best_day")
    day_labels   = dow.get("day_labels", [])

    len_labels = {
        "short":    "shorter sessions (under 30 min)",
        "medium":   "30–60 minute sessions",
        "long":     "60–90 minute sessions",
        "marathon": "longer sessions (90+ min)",
    }

    parts = []

    # opening — trend
    if trend == "improving":
        slope = abs(forecast.get("slope", 0))
        parts.append(
            f"You're trending upward, picking up about {slope:.1f} points per session — "
            "keep whatever you're doing right now."
        )
    elif trend == "declining":
        parts.append(
            "Your scores have dipped a bit lately, which is normal. "
            "A small tweak to your routine is usually enough to reverse it."
        )
    else:
        avg_str = f" around {overall_avg:.0f}" if overall_avg else ""
        parts.append(
            f"Your scores have been steady{avg_str} — solid foundation. "
            "The next step is finding where to squeeze out a few more points."
        )

    # sweet-spot conditions
    if best_period and best_len:
        parts.append(
            f"You score best in the {best_period} during {len_labels.get(best_len, best_len)}, "
            "so that's the slot worth protecting."
        )
    elif best_period:
        parts.append(f"Your sharpest focus tends to be in the {best_period} — guard that window.")

    # what the model says matters most
    features = fi.get("features", [])
    if features and not fi.get("error"):
        top_feat = features[0]
        pct      = top_feat["importance_pct"]
        feat_key = top_feat["feature"]
        if feat_key in ("hour", "day_of_week"):
            day_tip = f"on {day_labels[best_day]}s" if best_day is not None and day_labels else "on your stronger days"
            parts.append(
                f"Timing is actually your biggest lever — it accounts for {pct:.0f}% of your score variation. "
                f"Getting in a session {day_tip} in the {best_period or 'morning'} is worth more than eliminating most distractions."
            )
        elif feat_key == "duration":
            parts.append(
                f"Session length drives {pct:.0f}% of your score variance — more than any individual distraction. "
                f"{len_labels.get(best_len, 'Your usual length').capitalize()} seem to be your sweet spot."
            )
        else:
            # distraction-type feature — check if it matches the most frequent one
            feat_label = top_feat["label"]
            if top_dist and top_dist.lower() in feat_label.lower():
                # most frequent AND most impactful — straightforward advice
                parts.append(
                    f"{feat_label} are both your most frequent distraction and your biggest score drain ({pct:.0f}% impact). "
                    "Even reducing them by half would noticeably lift your average."
                )
            else:
                # different distraction is more impactful than the most frequent
                freq_note = f"you get distracted by {top_dist} more often" if top_dist else ""
                parts.append(
                    f"Interestingly, {feat_label} hurt your score the most ({pct:.0f}% impact)"
                    + (f" — even though {freq_note}" if freq_note else "") + ". "
                    "Cutting those down would do more for your score than anything else."
                )

    # forecast close
    preds = forecast.get("predicted_next_5", [])
    if preds and not forecast.get("error"):
        direction = forecast.get("direction")
        if direction == "improving":
            parts.append(
                f"Based on your trajectory, you're on track to hit around {preds[-1]:.0f} over your next five sessions."
            )
        elif direction == "declining":
            parts.append(
                f"The model projects around {preds[-1]:.0f} over the next five sessions if the pattern holds. "
                "A lower-stakes session with no pressure often breaks that slide."
            )
        else:
            parts.append(f"Your scores are projected to stay around {preds[-1]:.0f} — consistent, with room to grow.")

    return " ".join(parts)


def generate_brief_feedback(session_report: dict, pattern_analysis: dict | None) -> str:
    score       = session_report.get("score", 0) or 0
    focus_pct   = session_report.get("focus_percentage", 0) or 0
    events      = session_report.get("events", 0) or 0

    # --- score sentence ---
    overall_avg = None
    if pattern_analysis:
        overall_avg = pattern_analysis.get("trend", {}).get("overall_avg")

    if overall_avg is not None:
        if score >= overall_avg + 5:
            score_line = (
                f"Great session! You scored {score} — "
                f"{score - overall_avg:.0f} pts above your average of {overall_avg:.0f}."
            )
        elif score <= overall_avg - 5:
            score_line = (
                f"Tough one — your score of {score} was "
                f"{overall_avg - score:.0f} pts below your average of {overall_avg:.0f}."
            )
        else:
            score_line = f"Solid session with a score of {score}, right on your average of {overall_avg:.0f}."
    else:
        score_line = f"Session complete — you scored {score}."

    # --- distraction sentence ---
    dist_counts = {
        "Phone":       session_report.get("phone_distractions", 0) or 0,
        "Looking away": session_report.get("look_away_distractions", 0) or 0,
        "Left desk":   session_report.get("left_desk_distractions", 0) or 0,
        "App switch":  session_report.get("app_distractions", 0) or 0,
        "Idle":        session_report.get("idle_distractions", 0) or 0,
    }
    top_dist = max(dist_counts, key=dist_counts.get)
    top_count = dist_counts[top_dist]

    if events == 0:
        dist_line = "Zero distractions — incredible focus!"
    elif top_count > 0:
        dist_line = f"{top_dist} distractions were your main issue today ({top_count}×)."
    else:
        dist_line = f"{events} distraction{'s' if events != 1 else ''} logged."

    return f"{score_line} {dist_line}"
