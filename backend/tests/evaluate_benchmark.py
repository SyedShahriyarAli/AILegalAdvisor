import json
import os
import random
import re
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
import sys

# Ensure backend path is in sys.path so we can import app modules
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.graph_rag.legal_graph_rag import LegalGraphRAG

def load_benchmark_data():
    generated_dataset_path = BASE_DIR / "data" / "generated" / "benchmark_dataset.json"
    canonical_dataset_path = BASE_DIR / "data" / "jsons" / "benchmark_dataset.json"
    dataset_path = (
        generated_dataset_path if generated_dataset_path.exists() else canonical_dataset_path
    )
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_section_number(gold_passage: str) -> str:
    """Extracts '11' from 'Section 11, PECA 2016/2025'"""
    # Look for "Section <number>"
    match = re.search(r'Section\s+([\w\d]+)', gold_passage, re.IGNORECASE)
    if match:
        return match.group(1).lower().strip()
    return gold_passage.lower().strip()


def parse_yes_no_label(model_answer: str, prefix_chars: int = 500) -> str:
    """
    Normalize model output to 'yes' or 'no' for scoring.

    Handles fine-tuned prefixes like 'Answer Yes ...' and terse 'Yes' / 'No'.
    Uses the first whole-word yes/no within the leading prefix so later
    prose ('... not only X ...') does not flip the label.
    """
    s = (model_answer or "").strip().lower()
    if not s:
        return ""
    prefix = s[:prefix_chars]
    tokens = prefix.split()

    if len(tokens) >= 2 and tokens[0] == "answer" and tokens[1] in ("yes", "no"):
        return tokens[1]

    yes_m = re.search(r"\byes\b", prefix)
    no_m = re.search(r"\bno\b", prefix)
    if yes_m and no_m:
        return "yes" if yes_m.start() < no_m.start() else "no"
    if yes_m:
        return "yes"
    if no_m:
        return "no"

    if tokens and tokens[0] in ("yes", "no"):
        return tokens[0]
    return ""


def evaluate():
    load_dotenv(BASE_DIR / ".env")
    
    # Initialize RAG
    print("Initializing LegalGraphRAG...")
    rag = LegalGraphRAG(
        neo4j_uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        neo4j_user=os.getenv('NEO4J_USER', 'neo4j'),
        neo4j_password=os.getenv('NEO4J_PASSWORD', 'password'),
        ollama_url=os.getenv('OLLAMA_URL', 'http://localhost:11434'),
        ollama_model=os.getenv('OLLAMA_MODEL', 'Llama3.1:8b')
    )
    
    all_benchmark_cases = load_benchmark_data()
    sample_size = min(30, len(all_benchmark_cases))
    # Seed so successive runs (e.g. anchor-only vs anchor+weights) sample the
    # same questions and any delta is attributable to retrieval changes only.
    seed_value = int(os.getenv("RETRIEVAL_BENCHMARK_SEED", "42"))
    sampler = random.Random(seed_value)
    benchmark_data = sampler.sample(all_benchmark_cases, sample_size)
    print(
        f"Evaluating {sample_size} randomly sampled test cases "
        f"(full benchmark has {len(all_benchmark_cases)}, seed={seed_value})."
    )
    
    results = []
    correct_generation = 0
    total_recall = 0.0
    
    for i, test_case in enumerate(benchmark_data):
        query = test_case['query']
        expected_answer = test_case['answer'].strip().lower()
        gold_passages = test_case.get('gold_passages', [])
        
        print(f"\n[{i+1}/{len(benchmark_data)}] Evaluating Query: {query}")
        
        # 1. Evaluate Retrieval
        retrieved_docs = rag.multi_stage_retrieval(query, top_k=10)
        
        # Extract the expected section numbers
        expected_sections = [extract_section_number(g) for g in gold_passages]
        
        # Extract the retrieved section numbers
        retrieved_sections = []
        for doc in retrieved_docs:
            if 'article_number' in doc and doc['article_number']:
                retrieved_sections.append(str(doc['article_number']).lower().strip())
        
        # Calculate Recall
        if expected_sections:
            hits = sum(1 for exp in expected_sections if exp in retrieved_sections)
            recall = hits / len(expected_sections)
        else:
            recall = 1.0 # If no gold passages, default to 1.0
            
        total_recall += recall
        print(f"  -> Recall@10: {recall:.2%} (Expected: {expected_sections}, Retrieved: {retrieved_sections[:5]}...)")
        
        # 2. Evaluate Generation
        # Construct strict prompt
        context_text = "\n\n".join([f"Article {doc.get('article_number')}: {doc.get('content', '')}" for doc in retrieved_docs[:5]])
        
        prompt = f"""
Context from Pakistani Law:
{context_text}

Question: {query}

Instructions: Based on the context provided, answer the question with STRICTLY "Yes" or "No". Do not provide any other explanation or punctuation.
"""
        try:
            # Finetuned models may emit long rationales; keep enough budget for the opening "Answer Yes/No".
            model_output = rag._generate_text(
                prompt, temperature=0.1, num_predict=512
            ).strip().lower()
            if LegalGraphRAG.EMPTY_GENERATION_PLACEHOLDER.lower() in model_output:
                model_output = rag._generate_text(
                    prompt, temperature=0.1, num_predict=2048
                ).strip().lower()
        except Exception as e:
            print(f"  -> Generation request failed: {e}")
            model_output = LegalGraphRAG.EMPTY_GENERATION_PLACEHOLDER.lower()

        generation_failed = (
            LegalGraphRAG.EMPTY_GENERATION_PLACEHOLDER.lower() in model_output
        )
        if generation_failed:
            print(
                "  -> Warning: model returned no text. Verify Ollama is running, "
                "OLLAMA_MODEL is installed (`ollama pull <model>`), and OLLAMA_URL is correct."
            )

        # Clean punctuation
        model_answer = re.sub(r'[^\w\s]', '', model_output).strip()

        predicted_label = (
            "" if generation_failed else parse_yes_no_label(model_answer)
        )
        is_correct = not generation_failed and predicted_label == expected_answer
        if is_correct:
            correct_generation += 1

        preview = (model_answer[:120] + "…") if len(model_answer) > 120 else model_answer
        print(
            f"  -> Expected: {expected_answer.title()} | Parsed: {predicted_label or '(none)'} | "
            f"Correct: {is_correct} | Preview: {preview}"
        )
        
        results.append({
            "query": query,
            "expected_answer": expected_answer,
            "model_answer": model_answer,
            "predicted_label": predicted_label,
            "generation_failed": generation_failed,
            "is_correct": is_correct,
            "expected_sections": expected_sections,
            "retrieved_sections": retrieved_sections,
            "recall": recall
        })

    # Summary
    avg_recall = total_recall / len(benchmark_data) if benchmark_data else 0
    accuracy = correct_generation / len(benchmark_data) if benchmark_data else 0
    
    recall_percentage = f"{avg_recall * 100:.2f}%"
    accuracy_percentage = f"{accuracy * 100:.2f}%"
    
    print("\n" + "="*50)
    print("BENCHMARK EVALUATION RESULTS")
    print("="*50)
    print(f"Total Test Cases:            {len(benchmark_data)}")
    print(f"Average Retrieval Recall:    {recall_percentage}")
    print(f"Generation Accuracy:         {accuracy_percentage}")
    print("="*50)
    
    # Save results
    output_dir = BASE_DIR / "tests" / "evaluation_results"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"benchmark_eval_{timestamp}.json"
    
    report_data = {
        "summary": {
            "total_cases": len(benchmark_data),
            "average_recall_10_score": avg_recall,
            "average_recall_10_percentage": recall_percentage,
            "generation_accuracy_score": accuracy,
            "generation_accuracy_percentage": accuracy_percentage
        },
        "details": results
    }
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4)
        
    print(f"\nDetailed report saved to: {out_file}")

if __name__ == "__main__":
    evaluate()
