import json
import math
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from app.graph_rag.state import GraphState
from app.graph_rag.query_classifier import QueryComplexityClassifier
from app.graph_rag.legal_graph_rag import LegalGraphRAG

from langchain_core.runnables import RunnableConfig

# Node Functions

def classify_query(state: GraphState) -> Dict[str, Any]:
    """
    Classify the user's query complexity to guide retrieval.
    """
    print("---CLASSIFYING QUERY---")
    question = state["question"]
    classifier = QueryComplexityClassifier()
    complexity = classifier.classify(question)
    
    print(f"Complexity: {complexity}")
    return {"complexity": complexity, "steps": ["classify"]}

def retrieve_statutes(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Retrieve relevant statutory articles (CrPC, PPC, etc.).
    """
    print("---RETRIEVING STATUTES---")
    rag: LegalGraphRAG = config["configurable"]["rag"]
    question = state["question"]
    complexity = state["complexity"]
    
    # Adjust top_k based on complexity
    top_k = 10 if complexity == "complex" else 5
    
    # 1. Semantic Search (Statutes)
    semantic_docs = rag.semantic_search(question, top_k=top_k)
    
    # 2. Keyword Search (Statutes)
    keyword_docs = rag.keyword_search(question, top_k=top_k)
    
    # 3. Merge and Deduplicate
    all_statutes = {d["id"]: d for d in semantic_docs}
    for d in keyword_docs:
        if d["id"] not in all_statutes:
            all_statutes[d["id"]] = d
        else:
            # Boost score if found in both
            all_statutes[d["id"]]["combined_score"] = (
                all_statutes[d["id"]].get("similarity", 0) + 0.5
            )
            
    statutes = list(all_statutes.values())
    
    # Sort by score
    statutes.sort(key=lambda x: x.get("combined_score", x.get("similarity", 0)), reverse=True)
    statutes = statutes[:top_k+5] # Keep top results
    
    print(f"Found {len(statutes)} statutes")
    return {"statutes": statutes, "steps": ["retrieve_statutes"]}

def retrieve_cases(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Retrieve relevant court cases/judgments.
    """
    print("---RETRIEVING CASES---")
    rag: LegalGraphRAG = config["configurable"]["rag"]
    question = state["question"]
    
    # Explicit case law search
    # Using the specific methods exposed in LegalGraphRAG
    semantic_cases = rag.case_semantic_search(question, top_k=5)
    keyword_cases = rag.case_keyword_search(question, top_k=3)
    
    # Combine and deduplicate
    all_cases = {c["id"]: c for c in semantic_cases}
    for c in keyword_cases:
        if c["id"] not in all_cases:
            all_cases[c["id"]] = c
            
    cases = list(all_cases.values())
    print(f"Found {len(cases)} cases")
    return {"cases": cases, "steps": ["retrieve_cases"]}

def grade_and_combine(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Combine statutes and cases, and perform a basic relevance check.
    """
    print("---GRADING & COMBINING---")
    rag: LegalGraphRAG = config["configurable"]["rag"]
    question = state["question"]
    statutes = state.get("statutes", [])
    cases = state.get("cases", [])
    
    # Deduplicate Statutes
    unique_statutes = {}
    for doc in statutes:
        if doc["id"] not in unique_statutes:
            doc["type"] = "article"
            unique_statutes[doc["id"]] = doc
    
    statute_list = list(unique_statutes.values())
    if statute_list:
        statute_list = rag.rerank(question, statute_list, top_k=5, threshold=0.20)
        # Same issue as cases: narrative queries often score below the cross-encoder bar.
        if not statute_list:
            raw_statutes = list(unique_statutes.values())
            raw_statutes.sort(
                key=lambda x: float(
                    x.get("similarity", x.get("combined_score", x.get("score", 0)))
                ),
                reverse=True,
            )
            statute_list = raw_statutes[:5]
            for doc in statute_list:
                if doc.get("similarity") is not None:
                    doc["final_score"] = float(doc["similarity"])
                elif doc.get("combined_score") is not None:
                    doc["final_score"] = float(doc["combined_score"])
                else:
                    sc = float(doc.get("score", 0))
                    doc["final_score"] = (
                        1.0 - math.exp(-sc / 8.0) if sc > 0 else 0.0
                    )

    # Safety net: long narratives can produce empty statute results upstream
    # (semantic + keyword both return nothing or Lucene rejects the query),
    # which leaves applicable_laws/sources empty in the API response. When
    # that happens, fall back to multi_stage_retrieval which has citation
    # anchoring and graph expansion baked in, and keep only articles since
    # cases are handled by retrieve_cases.
    if not statute_list:
        try:
            backup_docs = rag.multi_stage_retrieval(question, top_k=5)
        except Exception as e:
            print(f"Statute backfill via multi_stage_retrieval failed: {e}")
            backup_docs = []
        statute_list = [d for d in backup_docs if d.get("type") != "case"][:5]
        for doc in statute_list:
            doc["type"] = "article"
            if doc.get("final_score") is None:
                doc["final_score"] = float(
                    doc.get("combined_score", doc.get("similarity", 0)) or 0.0
                )
        if statute_list:
            print(f"Statute backfill recovered {len(statute_list)} article(s) via multi_stage_retrieval")

    # Deduplicate Cases
    unique_cases = {}
    for doc in cases:
        if doc["id"] not in unique_cases:
            doc["type"] = "case"
            unique_cases[doc["id"]] = doc
            
    case_list = list(unique_cases.values())
    if case_list:
        case_list = rag.rerank(question, case_list, top_k=5, threshold=0.20)
        # Narrative intake queries often score low on the cross-encoder vs. long judgments;
        # if everything is filtered out, fall back to vector/keyword order so UI still shows precedents.
        if not case_list:
            # Reranker used threshold 0.20 on a blended score; narrative vs. judgment text often fails that bar.
            # Fall back to retrieval order, but always set final_score for the API/UI from vector similarity or keyword score.
            raw_cases = list(unique_cases.values())
            raw_cases.sort(
                key=lambda x: float(x.get("similarity", x.get("score", 0))),
                reverse=True,
            )
            case_list = raw_cases[:5]
            for doc in case_list:
                if doc.get("similarity") is not None:
                    doc["final_score"] = float(doc["similarity"])
                else:
                    sc = float(doc.get("score", 0))
                    # Full-text scores are unbounded; squash to (0,1) for display consistency
                    doc["final_score"] = 1.0 - math.exp(-sc / 8.0) if sc > 0 else 0.0
    
    # Combine for Context (Statutes first, then Cases)
    final_docs = statute_list + case_list
            
    print(f"Total unique documents: {len(final_docs)} ({len(statute_list)} statutes, {len(case_list)} cases)")
    
    # Update state with refined lists
    return {
        "documents": final_docs, 
        "statutes": statute_list,
        "cases": case_list,
        "steps": ["grade_and_combine"]
    }

def generate_answer(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Generate the final answer using the retrieved documents.
    """
    print("---GENERATING ANSWER---")
    rag: LegalGraphRAG = config["configurable"]["rag"]
    question = state["question"]
    documents = state["documents"]
    
    if not documents:
        return {
            "answer": "I could not find any relevant legal documents to answer your question. Please try rephrasing or asking about a specific legal section.",
            "is_satisfactory": False,
            "steps": ["generate_answer"]
        }
    
    # Use the RAG's context builder which handles formatting nicely
    context = rag.build_context(documents, query=question, max_words=2000)
    
    # Generate (advisory answers are JSON per system prompt)
    answer = rag.generate_answer_ollama(question, context, response_format="json")

    # Basic validation
    is_satisfactory = False
    if answer.strip().startswith("{"):
        try:
            obj = json.loads(answer)
            da = (obj.get("directAnswer") or "").strip()
            lb = obj.get("legalBasis") or []
            is_satisfactory = len(da) > 30 or (isinstance(lb, list) and len(lb) > 0)
        except json.JSONDecodeError:
            is_satisfactory = len(answer) > 50
    else:
        is_satisfactory = len(answer) > 50 and "not found" not in answer.lower()
    
    return {
        "answer": answer,
        "is_satisfactory": is_satisfactory,
        "steps": ["generate_answer"]
    }

# Workflow Construction

def create_legal_graph():
    """
    Constructs and compiles the LangGraph workflow.
    """
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("classify", classify_query)
    workflow.add_node("retrieve_statutes", retrieve_statutes)
    workflow.add_node("retrieve_cases", retrieve_cases)
    workflow.add_node("grade_documents", grade_and_combine)
    workflow.add_node("generate", generate_answer)
    
    # Add edges
    workflow.set_entry_point("classify")
    
    # Parallel Retrieval Branching
    # From classification, we go to BOTH retrieve_statutes and retrieve_cases
    workflow.add_edge("classify", "retrieve_statutes")
    workflow.add_edge("classify", "retrieve_cases")
    
    # Fan-in: Both retrievers go to grader
    workflow.add_edge("retrieve_statutes", "grade_documents")
    workflow.add_edge("retrieve_cases", "grade_documents")
    
    # Linear flow for the rest
    workflow.add_edge("grade_documents", "generate")
    workflow.add_edge("generate", END)
    
    # Compile
    app = workflow.compile()
    return app
