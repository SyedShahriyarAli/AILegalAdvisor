import os
import json
import time
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TEMPERATURE = float(os.environ.get("GEMINI_TEMPERATURE", "0.2")) # Low temp for consistency
GEMINI_MAX_OUTPUT_TOKENS = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "65536"))

BATCH_SIZE = 5
GENERATED_DATA_DIR = BASE_DIR / "data" / "generated"
INPUT_FILE = GENERATED_DATA_DIR / "finetuning_dataset.json"
OUTPUT_FILE = GENERATED_DATA_DIR / "benchmark_dataset.json"

def _strip_json_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()

def generate_benchmark_batch(batch, model, generation_config):
    prompt = f"""
You are an expert legal dataset generator.
I am providing you with a batch of {len(batch)} training examples containing complex legal scenarios and their legal outcomes under Pakistani cybercrime law (PECA).
Your task is to convert each example into a Yes/No question following the methodology of the "Housing Statute QA" benchmark.

For EACH example, generate:
1. A Yes/No `query` derived from the scenario and the legal outcome. The query should ask if a specific action in the scenario constitutes a specific offense under PECA, or if a specific section applies.
2. The `answer` to the query, which MUST be either strictly "Yes" or strictly "No".
3. A list of `gold_passages`, which are the applicable PECA sections mentioned in the output. For example: ["Section 11, PECA 2016", "Section 10, PECA 2016"]
4. The `scenario_context`, which is just a copy of the original user scenario (the `input`).

OUTPUT FORMAT:
Return a valid JSON array containing exactly {len(batch)} JSON objects:
[
  {{
    "query": "[Yes/No Question]",
    "answer": "[Yes or No]",
    "gold_passages": ["[Section X, PECA YEAR]", ...],
    "scenario_context": "[Original input scenario]"
  }},
  ...
]

Here are the {len(batch)} examples:
"""
    for i, ex in enumerate(batch):
        prompt += f"\n\nEXAMPLE {i+1}:\n"
        prompt += f"Scenario (input): {ex.get('input')}\n"
        prompt += f"Legal Outcome (output): {ex.get('output')}\n"

    prompt += "\n\nPlease generate the JSON array now. Ensure it strictly follows the OUTPUT FORMAT and contains valid JSON."

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

    try:
        result_text = (response.text or "").strip()
    except ValueError:
        print("Error: Could not read response text (blocked or empty candidates).")
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
            return repaired
        except Exception as repair_err:
            print(f"Error: Gemini returned invalid JSON: {e}")
            return None

def main():
    if not GEMINI_API_KEY:
        raise SystemExit("Set GEMINI_API_KEY in backend/.env")

    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    generation_config = genai.GenerationConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        response_mime_type="application/json",
    )

    GENERATED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        print(f"Input file {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        finetuning_data = json.load(f)

    print(f"Loaded {len(finetuning_data)} examples from {INPUT_FILE.name}")

    results = []
    batches = [finetuning_data[i : i + BATCH_SIZE] for i in range(0, len(finetuning_data), BATCH_SIZE)]

    print(f"Generating benchmark dataset in {len(batches)} batches...")

    for batch_idx, batch in enumerate(batches):
        print(f"Processing batch {batch_idx + 1}/{len(batches)} ({len(batch)} examples)")
        batch_results = generate_benchmark_batch(batch, model, generation_config)
        
        if batch_results and isinstance(batch_results, list):
            if len(batch_results) != len(batch):
                print(f"  -> Expected {len(batch)} examples, got {len(batch_results)}. Saving what we got.")
            results.extend(batch_results)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            print(f"  -> Added {len(batch_results)} examples. Total: {len(results)}")
        else:
            print("  -> Failed to generate valid batch results.")
        
        time.sleep(1)

    print(f"\nDone! Benchmark dataset saved to {OUTPUT_FILE} with {len(results)} examples.")

if __name__ == "__main__":
    main()
