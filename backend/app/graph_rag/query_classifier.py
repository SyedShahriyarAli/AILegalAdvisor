"""
Query Complexity Classifier
Analyzes legal questions and classifies them by complexity
to enable adaptive retrieval strategies
"""

import re
from typing import Literal

ComplexityLevel = Literal['simple', 'moderate', 'complex']

class QueryComplexityClassifier:
    """
    Classifies legal queries into simple, moderate, or complex
    based on linguistic patterns and legal terminology
    """
    
    def __init__(self):
        # Patterns that indicate specific section/article references
        self.section_patterns = [
            r'\bsection\s+\d+[A-Z]*\b',
            r'\barticle\s+\d+[A-Z]*\b',
            r'\bclause\s+\([a-z0-9]+\)',
            r'\bpara\s+\d+\b',
            r'\bparagraph\s+\d+\b'
        ]
        
        # Keywords that indicate complex multi-domain queries
        self.complexity_indicators = [
            # Conditional/comparative
            'but', 'however', 'except', 'unless', 'whereas', 'although',
            # Multi-part questions
            'and also', 'as well as', 'in addition', 'furthermore',
            # Hypothetical scenarios
            'what if', 'suppose', 'in case', 'scenario',
            # Multiple legal areas
            'both', 'either', 'neither', 'combination'
        ]
        
        # Legal terms that suggest moderate complexity
        self.legal_terms = [
            'bail', 'custody', 'prosecution', 'defendant', 'plaintiff',
            'evidence', 'witness', 'testimony', 'appeal', 'jurisdiction',
            'liability', 'damages', 'contract', 'tort', 'statute',
            'precedent', 'ruling', 'judgment', 'decree', 'writ'
        ]
    
    def classify(self, query: str) -> ComplexityLevel:
        """
        Classify query complexity
        
        Args:
            query: User's legal question
            
        Returns:
            'simple', 'moderate', or 'complex'
        """
        query_lower = query.lower()
        word_count = len(query.split())
        
        # Check for specific section references (SIMPLE)
        if self._has_specific_reference(query):
            return 'simple'
        
        # Check for complexity indicators (COMPLEX)
        complexity_score = self._calculate_complexity_score(query_lower)
        
        if complexity_score >= 3:
            return 'complex'
        
        # Long questions are usually complex
        if word_count > 20:
            return 'complex'
        
        # Multiple questions or clauses
        question_marks = query.count('?')
        if question_marks > 1:
            return 'complex'
        
        # Check for legal terminology (MODERATE if found)
        has_legal_terms = any(term in query_lower for term in self.legal_terms)
        
        if has_legal_terms:
            if word_count > 12 or complexity_score >= 1:
                return 'moderate'
            else:
                return 'simple'
        
        # Very short questions
        if word_count <= 5:
            return 'simple'
        
        # Default to moderate
        return 'moderate'
    
    def _has_specific_reference(self, query: str) -> bool:
        """Check if query references a specific section/article"""
        for pattern in self.section_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    def _calculate_complexity_score(self, query: str) -> int:
        """Calculate complexity score based on indicators"""
        score = 0
        
        # Check for complexity indicators
        for indicator in self.complexity_indicators:
            if indicator in query:
                score += 1
        
        # Check for multiple "and" conjunctions
        and_count = query.count(' and ')
        if and_count >= 2:
            score += 1
        
        # Check for conditional words
        conditionals = ['if', 'when', 'where', 'whether']
        conditional_count = sum(1 for word in conditionals if f' {word} ' in f' {query} ')
        if conditional_count >= 2:
            score += 1
        
        return score
    
    def get_retrieval_strategy(self, query: str) -> dict:
        """
        Get recommended retrieval strategy based on complexity
        
        Returns:
            dict with recommended parameters
        """
        complexity = self.classify(query)
        
        strategies = {
            'simple': {
                'complexity': 'simple',
                'use_multi_stage': False,
                'top_k': 5,
                'max_words': 1000,
                'description': 'Direct lookup - fast retrieval'
            },
            'moderate': {
                'complexity': 'moderate',
                'use_multi_stage': True,
                'top_k': 10,
                'max_words': 1500,
                'description': 'Balanced retrieval with re-ranking'
            },
            'complex': {
                'complexity': 'complex',
                'use_multi_stage': True,
                'top_k': 15,
                'max_words': 2000,
                'description': 'Comprehensive multi-stage retrieval'
            }
        }
        
        return strategies[complexity]
    
    def explain_classification(self, query: str) -> str:
        """
        Explain why a query was classified a certain way
        
        Returns:
            Human-readable explanation
        """
        complexity = self.classify(query)
        query_lower = query.lower()
        word_count = len(query.split())
        
        reasons = []
        
        if self._has_specific_reference(query):
            reasons.append("references specific section/article")
        
        complexity_score = self._calculate_complexity_score(query_lower)
        if complexity_score > 0:
            reasons.append(f"has {complexity_score} complexity indicator(s)")
        
        if word_count > 20:
            reasons.append(f"long question ({word_count} words)")
        elif word_count <= 5:
            reasons.append(f"short question ({word_count} words)")
        
        if query.count('?') > 1:
            reasons.append("multiple questions")
        
        legal_term_count = sum(1 for term in self.legal_terms if term in query_lower)
        if legal_term_count > 0:
            reasons.append(f"contains {legal_term_count} legal term(s)")
        
        reason_str = ", ".join(reasons) if reasons else "general query pattern"
        
        return f"Classified as '{complexity}' because: {reason_str}"


# Example usage and testing
if __name__ == "__main__":
    classifier = QueryComplexityClassifier()
    
    test_queries = [
        "What is Section 497?",
        "Can I get bail?",
        "What is the punishment for theft?",
        "Can I get bail if accused of theft?",
        "What are the bail conditions for murder with self-defense claim?",
        "If someone is accused of robbery but claims self-defense, can they get bail, and what evidence is needed?",
        "What is the difference between Section 302 and Section 304 PPC?",
        "Tell me about anticipatory bail",
        "When can pre-arrest bail be granted and what are the conditions?",
        "What happens if I violate bail conditions?"
    ]
    
    print("Query Complexity Classifier - Test Cases")
    print("=" * 80)
    
    for query in test_queries:
        complexity = classifier.classify(query)
        strategy = classifier.get_retrieval_strategy(query)
        explanation = classifier.explain_classification(query)
        
        print(f"\nQuery: {query}")
        print(f"Complexity: {complexity.upper()}")
        print(f"Strategy: {strategy['description']}")
        print(f"  - Multi-stage: {strategy['use_multi_stage']}")
        print(f"  - Top-K: {strategy['top_k']}")
        print(f"  - Max words: {strategy['max_words']}")
        print(f"Reason: {explanation}")
        print("-" * 80)
