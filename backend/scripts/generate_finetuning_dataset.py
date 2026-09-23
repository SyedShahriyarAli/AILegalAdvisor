import os
import json
import random
import time
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TEMPERATURE = float(os.environ.get("GEMINI_TEMPERATURE", "0.7"))
GEMINI_MAX_OUTPUT_TOKENS = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "65536"))

FINETUNE_BATCH_SIZE = int(os.environ.get("FINETUNE_BATCH_SIZE", "5"))
# 0 = do not truncate case pdf_data (only PECA is guaranteed full; cases can be huge)
FINETUNE_CASE_PDF_MAX_CHARS = int(os.environ.get("FINETUNE_CASE_PDF_MAX_CHARS", "0"))

CANONICAL_DATA_DIR = BASE_DIR / "data" / "jsons"
GENERATED_DATA_DIR = BASE_DIR / "data" / "generated"
DEFAULT_OUTPUT_FILE = GENERATED_DATA_DIR / "finetuning_dataset.json"
OUTPUT_FILE = Path(os.environ.get("FINETUNE_OUTPUT", str(DEFAULT_OUTPUT_FILE)))
PROMPT_FILE = BASE_DIR.parent / ".agents" / "rules" / "finetunning-dataset-creation-prompt.md"
# Append to OUTPUT_FILE and skip judgments already present (by court + case_no).
FINETUNE_APPEND = os.environ.get("FINETUNE_APPEND", "1") == "1"
# Max new examples this run; unset = use all remaining judgments not yet in the dataset.
FINETUNE_NEW_LIMIT = os.environ.get("FINETUNE_NEW_LIMIT")
# When FINETUNE_APPEND=0, reproducible sample of valid_cases (same as before).
FINETUNE_RANDOM_SEED = os.environ.get("FINETUNE_RANDOM_SEED", "42")
# Max judgments to draw from the pool on a fresh run (FINETUNE_APPEND=0); ignored when appending.
FINETUNE_SAMPLE_CAP = int(os.environ.get("FINETUNE_SAMPLE_CAP", "100"))
# If 1, skip an example when user "input" matches an existing row (normalized).
FINETUNE_DEDUPE_INPUT = os.environ.get("FINETUNE_DEDUPE_INPUT", "0") == "1"
# How many training rows to allow per judgment (same court+case_no). Increase to revisit cases with new scenarios.
FINETUNE_MAX_VARIATIONS_PER_CASE = int(os.environ.get("FINETUNE_MAX_VARIATIONS_PER_CASE", "2"))


def load_data():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    with open(CANONICAL_DATA_DIR / "peca-act-2016.json", "r", encoding="utf-8") as f:
        peca_data = json.load(f)

    with open(GENERATED_DATA_DIR / "all_courts_cyber_cases_enriched.json", "r", encoding="utf-8") as f:
        cases_data = json.load(f)

    return system_prompt, peca_data, cases_data


def build_clean_peca(peca_data):
    """Full statute structure for the prompt (no shortening)."""
    clean_peca = []
    for section in peca_data.get("document", {}).get("sections", []):
        clean_peca.append({
            "section": section.get("section_number"),
            "title": section.get("title"),
            "content": section.get("content"),
            "clauses": section.get("clauses"),
        })
    return clean_peca


def prepare_case_for_prompt(case):
    c = dict(case)
    if FINETUNE_CASE_PDF_MAX_CHARS > 0:
        pd = c.get("pdf_data") or ""
        if len(pd) > FINETUNE_CASE_PDF_MAX_CHARS:
            c["pdf_data"] = pd[: FINETUNE_CASE_PDF_MAX_CHARS]
    return c


def normalize_case_key(court, case_no):
    court = (court or "").strip()
    case_no = " ".join(str(case_no or "").split())
    return (court, case_no)


def case_key_from_case(case):
    return normalize_case_key(case.get("court"), case.get("case_no"))


def normalized_input_key(text):
    if not text:
        return ""
    return " ".join(str(text).split()).strip().lower()


def load_existing_dataset(path):
    """Returns (results list, case_row_counts, seen_inputs).

    case_row_counts maps (court, case_no) -> number of examples already stored for that judgment.
    """
    if not path.exists():
        return [], {}, set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return [], {}, set()
    case_row_counts = {}
    seen_inputs = set()
    for ex in data:
        meta = ex.get("_metadata") or {}
        key = normalize_case_key(meta.get("source_court"), meta.get("source_case_no"))
        if key != ("", ""):
            case_row_counts[key] = case_row_counts.get(key, 0) + 1
        inp = ex.get("input")
        if inp:
            seen_inputs.add(normalized_input_key(inp))
    return data, case_row_counts, seen_inputs


def _strip_json_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


def generate_example_batch(
    cases_batch,
    peca_subset,
    system_prompt,
    model,
    generation_config,
    variation_targets,
):
    """variation_targets: list of 1-based indices (this row will be the Nth example for that judgment)."""
    prompt = f"""
{system_prompt}

IMPORTANT BATCH INSTRUCTION:
You are provided with a batch of {len(cases_batch)} cases. You must generate exactly ONE training example for EACH case.
Your output MUST be a valid JSON array containing exactly {len(cases_batch)} JSON objects following the OUTPUT FORMAT.
Across rows, vary user voice and concrete scenario details; avoid copy-paste openings or interchangeable boilerplate between examples.

"""
    for i, vn in enumerate(variation_targets):
        prompt += (
            f"For CASE {i + 1}, you are generating training variation #{vn} for that same judgment. "
        )
        if vn > 1:
            prompt += (
                "Earlier variations for this case may already exist elsewhere: do NOT produce a near-duplicate. "
                "Use a different user persona, question type (e.g. procedural steps vs defenses vs remedies vs evidence), "
                "and different opening phrasing. The `input` and `output` must be substantively new while still faithful "
                "to the case facts in the PDF. "
            )
        prompt += "\n"

    prompt += """
---
Here is the complete PECA JSON to reference (do not omit or summarize this statute text in your reasoning; use it as the legal ground truth):
""" + f"{json.dumps(peca_subset, ensure_ascii=False)}" + """

---
Here are the cases to extract scenarios from:
"""
    for i, case in enumerate(cases_batch):
        prompt += f"\n\nCASE {i+1}:\n{json.dumps(case, ensure_ascii=False)}"

    prompt += (
        "\n\nPlease generate a JSON array of training examples following the OUTPUT FORMAT strictly. "
        "The reply must be parseable JSON: inside every string value, use escaped newlines (\\n), "
        "never literal line breaks, and do not include raw tab or other control characters."
    )

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

    try:
        result_text = (response.text or "").strip()
    except ValueError:
        print("Error: Could not read response text (blocked or empty candidates).")
        if getattr(response, "prompt_feedback", None):
            print(f"  prompt_feedback: {response.prompt_feedback}")
        return None

    if not result_text:
        print("Error: Empty response from Gemini.")
        return None

    result_text = _strip_json_fences(result_text)

    try:
        return json.loads(result_text)
    except json.JSONDecodeError as e:
        try:
            import json_repair

            repaired = json_repair.loads(result_text)
            print(f"  -> Repaired non-strict JSON from model ({e}); using json_repair fallback.")
            return repaired
        except Exception as repair_err:
            print(f"Error: Gemini returned invalid JSON: {e}")
            print(f"  json_repair also failed: {repair_err}")
            print(f"Raw start: {result_text[:500]}...")
            return None


def main():
    if not GEMINI_API_KEY:
        raise SystemExit(
            "Set GEMINI_API_KEY in backend/.env (Google AI Studio key). "
            "Optional: GEMINI_MODEL, FINETUNE_BATCH_SIZE, FINETUNE_CASE_PDF_MAX_CHARS (0=no truncate), "
            "FINETUNE_APPEND, FINETUNE_NEW_LIMIT, FINETUNE_DEDUPE_INPUT, FINETUNE_MAX_VARIATIONS_PER_CASE."
        )

    try:
        import google.generativeai as genai
    except ImportError as e:
        raise SystemExit(
            "Missing google-generativeai. From backend/: uv sync"
        ) from e

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    generation_config = genai.GenerationConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        response_mime_type="application/json",
    )

    print(f"Using Gemini model {GEMINI_MODEL} (full PECA JSON in each request)")
    print("Loading data...")
    system_prompt, peca_data, cases_data = load_data()
    clean_peca = build_clean_peca(peca_data)
    peca_chars = len(json.dumps(clean_peca, ensure_ascii=False))
    print(f"PECA JSON size: {peca_chars} characters (not truncated).")

    valid_cases = [
        c for c in cases_data
        if c.get("pdf_data") and not str(c["pdf_data"]).startswith("[ERROR")
    ]
    print(f"Found {len(valid_cases)} valid cases with PDF data.")

    if not valid_cases:
        print("No valid cases found. Please ensure cases are enriched first.")
        return

    GENERATED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_FILE
    if FINETUNE_APPEND and output_file.exists():
        results, case_row_counts, seen_inputs = load_existing_dataset(output_file)
        n_keys = len(case_row_counts)
        print(
            f"Append mode: loaded {len(results)} existing examples from {output_file.name}; "
            f"{n_keys} judgment(s) with at least one row "
            f"(max {FINETUNE_MAX_VARIATIONS_PER_CASE} row(s) per judgment)."
        )
    else:
        results, case_row_counts, seen_inputs = [], {}, set()
        if not FINETUNE_APPEND:
            print(f"Fresh run (FINETUNE_APPEND=0): will overwrite {output_file.name}.")

    remaining = [
        c for c in valid_cases
        if case_row_counts.get(case_key_from_case(c), 0) < FINETUNE_MAX_VARIATIONS_PER_CASE
    ]
    print(
        f"Judgments still under cap ({FINETUNE_MAX_VARIATIONS_PER_CASE} row(s) each): {len(remaining)}."
    )

    if not remaining:
        print(
            "No judgments left under FINETUNE_MAX_VARIATIONS_PER_CASE. "
            "Raise it (e.g. FINETUNE_MAX_VARIATIONS_PER_CASE=2) to add new scenarios for the same cases "
            "without copying prior rows."
        )
        return

    if FINETUNE_APPEND:
        if os.environ.get("FINETUNE_RANDOM_SEED"):
            random.seed(int(os.environ["FINETUNE_RANDOM_SEED"]))
        else:
            random.seed()
    else:
        random.seed(int(FINETUNE_RANDOM_SEED))

    if not FINETUNE_APPEND and len(remaining) > FINETUNE_SAMPLE_CAP:
        remaining = random.sample(remaining, FINETUNE_SAMPLE_CAP)
        print(f"Fresh run: capped pool to {len(remaining)} judgments (FINETUNE_SAMPLE_CAP={FINETUNE_SAMPLE_CAP}).")

    if FINETUNE_NEW_LIMIT:
        new_limit = min(int(FINETUNE_NEW_LIMIT), len(remaining))
        sampled_cases = random.sample(remaining, new_limit)
    else:
        sampled_cases = remaining[:]
        random.shuffle(sampled_cases)

    batch_size = FINETUNE_BATCH_SIZE
    batches = [
        sampled_cases[i : i + batch_size] for i in range(0, len(sampled_cases), batch_size)
    ]

    print(
        f"Generating {len(sampled_cases)} new example(s) in {len(batches)} batch(es) "
        f"(batch_size={batch_size}, case_pdf_max_chars={FINETUNE_CASE_PDF_MAX_CHARS or 'unlimited'}, "
        f"dedupe_input={FINETUNE_DEDUPE_INPUT})..."
    )

    added_new = 0
    for batch_idx, batch in enumerate(batches):
        print(f"Processing batch {batch_idx + 1}/{len(batches)} ({len(batch)} cases)")
        prepared = [prepare_case_for_prompt(c) for c in batch]
        variation_targets = [
            case_row_counts.get(case_key_from_case(c), 0) + 1 for c in batch
        ]
        batch_examples = generate_example_batch(
            prepared,
            clean_peca,
            system_prompt,
            model,
            generation_config,
            variation_targets,
        )

        if batch_examples and isinstance(batch_examples, list):
            if len(batch_examples) != len(batch):
                print(
                    f"  -> Expected {len(batch)} examples, got {len(batch_examples)}; skipping batch."
                )
            else:
                batch_added = 0
                for i, example in enumerate(batch_examples):
                    if i >= len(batch):
                        break
                    in_key = normalized_input_key(example.get("input"))
                    if FINETUNE_DEDUPE_INPUT and in_key and in_key in seen_inputs:
                        print(
                            f"  -> Skip duplicate input (matches existing row); "
                            f"case {batch[i].get('case_no')!r}"
                        )
                        continue
                    ck = case_key_from_case(batch[i])
                    vn = case_row_counts.get(ck, 0) + 1
                    example["_metadata"] = {
                        "source_case_no": batch[i].get("case_no"),
                        "source_court": batch[i].get("court"),
                        "variation_index": vn,
                    }
                    case_row_counts[ck] = case_row_counts.get(ck, 0) + 1
                    if in_key:
                        seen_inputs.add(in_key)
                    results.append(example)
                    batch_added += 1
                    added_new += 1
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=4, ensure_ascii=False)
                print(
                    f"  -> Added {batch_added} example(s) from batch. "
                    f"Dataset total: {len(results)} (+{added_new} this run so far)"
                )
        else:
            print("  -> Failed to generate batch examples. Result was not a valid list.")
            if isinstance(batch_examples, dict):
                print("  -> (Model returned a single dictionary instead of a list)")

        time.sleep(1)

    print(f"\nDone. Dataset size: {len(results)} examples (+{added_new} new this run).")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
