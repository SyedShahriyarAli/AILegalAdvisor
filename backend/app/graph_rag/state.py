from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator

class GraphState(TypedDict):
    """
    Represents the state of the legal query processing graph.
    
    Attributes:
        question: The user's original question
        complexity: Classified complexity of the query (simple, moderate, complex)
        statutes: List of retrieved statutory articles
        cases: List of retrieved court cases
        documents: Combined and filtered list of documents for context
        answer: The generated answer
        steps: Annotated[List[str], operator.add]
        is_satisfactory: Boolean indicating if the answer passed quality checks
    """
    question: str
    complexity: str
    statutes: List[Dict[str, Any]]
    cases: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]
    answer: str
    steps: Annotated[List[str], operator.add]
    is_satisfactory: bool
