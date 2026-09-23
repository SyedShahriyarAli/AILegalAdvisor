"""
Metadata-only filter for tech law / cybercrime related court listings.
Used by LHC and Sindh scrapers before persisting judgments.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

FILTER_PROFILE = "cyber_law_v1"

# Multi-word and specific phrases: substring match after lowercasing.
PHRASES: tuple[str, ...] = (
    "prevention of electronic crimes",
    "electronic crimes act",
    "electronic crime",
    "cyber crime",
    "cybercrime",
    "cyber-crime",
    "cyber security",
    "cybersecurity",
    "computer crime",
    "online fraud",
    "electronic fraud",
    "identity theft",
    "electronic forgery",
    "digital forgery",
    "unauthorized access",
    "unauthorised access",
    "data theft",
    "data breach",
    "hacking",
    "phishing",
    "spoofing",
    "impersonation",
    "social media",
    "defamation on internet",
    "online defamation",
    "information technology",
    "electronic transaction",
    "cyber crime wing",
    "cybercrime wing",
    "cyber wing",
    "e-fraud",
    "efraud",
    "whatsapp",
    "facebook",
    "twitter",
    "instagram",
    "fake account",
    "morphing",
    "deepfake",
    "blackmail online",
    "sextortion",
)

# Short tokens matched with word boundaries to reduce false positives.
WORD_TOKENS: tuple[str, ...] = (
    "peca",
    "fia",
    "otp",
    "sim",
    "imei",
)


def normalize_text(s: str) -> str:
    if not s:
        return ""
    t = s.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def collect_cyber_law_triggers(blob: str) -> List[Tuple[str, str]]:
    """
    Return all (kind, value) matches: ('phrase', ...) or ('word_token', ...).
    Order: phrases in PHRASES order, then word tokens in WORD_TOKENS order.
    """
    out: List[Tuple[str, str]] = []
    if not blob:
        return out

    for phrase in PHRASES:
        if phrase in blob:
            out.append(("phrase", phrase))

    for tok in WORD_TOKENS:
        if re.search(rf"\b{re.escape(tok)}\b", blob):
            out.append(("word_token", tok))

    return out


def classify_cyber_law_listing(text_blob: str) -> Optional[Dict[str, Any]]:
    """
    If listing metadata matches the cyber-law filter, return audit fields; else None.

    Keys:
      filter_profile, triggers (list of {kind, matched}),
      primary_reason (one-line summary),
      reason (human-readable explanation for reviewers).
    """
    blob = normalize_text(text_blob)
    triggers_raw = collect_cyber_law_triggers(blob)
    if not triggers_raw:
        return None

    triggers = [{"kind": k, "matched": v} for k, v in triggers_raw]
    first_kind, first_val = triggers_raw[0]

    if first_kind == "phrase":
        primary = (
            f'Listing text contains phrase "{first_val}" '
            f'(substring match in combined fields; profile {FILTER_PROFILE}).'
        )
    else:
        primary = (
            f'Listing text contains token "{first_val}" as a whole word '
            f"(word-boundary match; profile {FILTER_PROFILE})."
        )

    if len(triggers_raw) > 1:
        extra = ", ".join(f'{t[0]}:{t[1]!r}' for t in triggers_raw[1:])
        primary += f" Additional triggers: {extra}."

    return {
        "filter_profile": FILTER_PROFILE,
        "triggers": triggers,
        "primary_reason": primary,
        "reason": primary,
    }


def judgment_matches_cyber_law(text_blob: str) -> bool:
    """
    Return True if normalized listing text matches cyber/tech-law heuristics.
    """
    blob = normalize_text(text_blob)
    return bool(collect_cyber_law_triggers(blob))


def lhc_listing_blob(j: Mapping[str, Any]) -> str:
    parts = [
        j.get("case_title") or "",
        j.get("writ_petition") or "",
        j.get("hon_judge") or "",
        j.get("lhc_citation") or "",
    ]
    return " ".join(str(p) for p in parts if p)


def sindh_listing_blob(j: Mapping[str, Any]) -> str:
    parts = [
        j.get("case_title") or "",
        j.get("case_number") or "",
        j.get("matter") or "",
        j.get("location") or "",
        j.get("judges") or "",
    ]
    return " ".join(str(p) for p in parts if p)


def lhc_judgment_matches(j: Dict[str, Any]) -> bool:
    return judgment_matches_cyber_law(lhc_listing_blob(j))


def sindh_judgment_matches(j: Dict[str, Any]) -> bool:
    return judgment_matches_cyber_law(sindh_listing_blob(j))


def lhc_cyber_classification(j: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    return classify_cyber_law_listing(lhc_listing_blob(j))


def sindh_cyber_classification(j: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    return classify_cyber_law_listing(sindh_listing_blob(j))


def attach_cyber_labels_to_judgment(
    judgment: Dict[str, Any],
    classification: Optional[Dict[str, Any]],
) -> None:
    """Mutate judgment dict in place with cyber-law audit fields when classified."""
    if not classification:
        return
    judgment["cyber_law_reason"] = classification["reason"]
    judgment["cyber_law_match"] = {
        "filter_profile": classification["filter_profile"],
        "triggers": classification["triggers"],
    }
