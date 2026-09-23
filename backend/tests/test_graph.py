
import sys
import os

# Add backend to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.graph_rag.graph import create_legal_graph
from app.graph_rag.state import GraphState
from unittest.mock import MagicMock

def test_graph_execution():
    print("Initializing Graph...")
    app = create_legal_graph()
    
    # Mock RAG system
    mock_rag = MagicMock()
    # Mock return values
    mock_rag.semantic_search.return_value = [
        {"id": "1", "title": "Article 1", "content": "Content 1", "type": "article"}
    ]
    mock_rag.keyword_search.return_value = []
    
    # Cases
    mock_rag.case_semantic_search.return_value = [
        {"id": "2", "title": "Case 1", "summary": "Summary 1", "type": "case"}
    ]
    # Reranker
    def mock_rerank(query, docs, top_k=10):
        return docs[:top_k]
    mock_rag.rerank.side_effect = mock_rerank
    mock_rag.case_keyword_search.return_value = []
    mock_rag.build_context.return_value = "Mock Context"
    mock_rag.generate_answer_ollama.return_value = "This is a valid legal answer that is long enough to pass validation."
    
    # Run the graph
    print("Running Graph...")
    initial_state = {"question": "What is the punishment for theft?", "steps": []}
    config = {"configurable": {"rag": mock_rag}}
    
    # Use invoke
    result = app.invoke(initial_state, config=config)
    
    print("\nGraph Execution Results:")
    print(f"Final Answer: {result.get('answer')}")
    print(f"Steps Taken: {result.get('steps')}")
    print(f"Documents: {len(result.get('documents', []))}")
    
    assert "classify" in result["steps"]
    assert "retrieve_statutes" in result["steps"]
    assert "retrieve_cases" in result["steps"]
    assert "generate_answer" in result["steps"]
    assert len(result["documents"]) == 2  # 1 statute + 1 case
    
    print("\n✅ Verification Successful: Graph compiled and executed correctly.")

if __name__ == "__main__":
    test_graph_execution()
