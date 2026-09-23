"""
Response Formatter - Improves answer quality and formatting
Filters irrelevant sources and formats responses better
"""

from typing import Dict, List, Any

class ResponseFormatter:
    """
    Formats and refines legal query responses
    - Filters irrelevant sources
    - Improves answer presentation
    - Ensures clean, professional output
    """
    
    # Relevance thresholds for filtering
    RELEVANCE_THRESHOLDS = {
        'high': 0.5,      # High confidence - definitely relevant
        'medium': 0.0,    # Medium confidence - possibly relevant
        'low': -2.0       # Low confidence - probably irrelevant
    }
    
    @staticmethod
    def filter_relevant_sources(sources: List[Dict], min_threshold: float = None) -> List[Dict]:
        """
        Filter sources based on relevance score
        
        Args:
            sources: List of source dictionaries with relevance_score
            min_threshold: Minimum relevance score (default: 0.0)
            
        Returns:
            Filtered list of relevant sources
        """
        if min_threshold is None:
            min_threshold = ResponseFormatter.RELEVANCE_THRESHOLDS['medium']
        
        # Filter out low-relevance sources
        relevant = [
            src for src in sources 
            if src.get('relevance_score', 0) >= min_threshold
        ]
        
        # If we filtered everything out, keep top 3 anyway
        if not relevant and sources:
            # Sort by score and take top 3
            sorted_sources = sorted(
                sources, 
                key=lambda x: x.get('relevance_score', 0), 
                reverse=True
            )
            relevant = sorted_sources[:3]
        
        return relevant
    
    @staticmethod
    def format_answer(raw_answer: str) -> str:
        """
        Clean and format the answer text
        
        Args:
            raw_answer: Raw answer from LLM
            
        Returns:
            Formatted answer with proper structure
        """
        if not raw_answer:
            return "No answer generated."
        
        # Remove excessive newlines
        answer = '\n'.join(line for line in raw_answer.split('\n') if line.strip())
        
        # Ensure proper spacing
        answer = answer.replace('\n\n\n', '\n\n')
        
        return answer.strip()
    
    @staticmethod
    def format_sources(sources: List[Dict]) -> List[Dict]:
        """
        Format source citations for clean presentation
        
        Args:
            sources: List of source dictionaries
            
        Returns:
            Formatted sources with cleaned fields
        """
        formatted = []
        
        for src in sources:
            formatted_src = {
                'document': src.get('document', 'Unknown'),
                'article': src.get('article', 'N/A'),
                'title': src.get('title', '').strip(),
                'relevance_score': round(float(src.get('relevance_score', 0)), 3)
            }
            
            # Only include optional fields if they exist and are useful
            if src.get('page_number'):
                formatted_src['page_number'] = src['page_number']
            
            if src.get('pdf_link'):
                formatted_src['pdf_link'] = src['pdf_link']
            
            # Only include source_file if it's not empty
            if src.get('source_file', '').strip():
                formatted_src['source_file'] = src['source_file']
            
            formatted.append(formatted_src)
        
        return formatted
    
    @staticmethod
    def enhance_response(response: Dict[str, Any], relevance_threshold: float = 0.0) -> Dict[str, Any]:
        """
        Main method to enhance complete query response
        
        Args:
            response: Raw response from RAG system
            relevance_threshold: Minimum relevance score for sources
            
        Returns:
            Enhanced response with filtered sources and formatted answer
        """
        # Filter sources by relevance
        original_sources = response.get('sources', [])
        filtered_sources = ResponseFormatter.filter_relevant_sources(
            original_sources, 
            relevance_threshold
        )
        
        # Format sources
        formatted_sources = ResponseFormatter.format_sources(filtered_sources)
        
        # Format answer
        formatted_answer = ResponseFormatter.format_answer(response.get('answer', ''))
        
        # Build enhanced response
        enhanced = {
            'answer': formatted_answer,
            'sources': formatted_sources,
            'success': True,
            'complexity': response.get('complexity', 'moderate'),
            'retrieval_strategy': response.get('retrieval_strategy', 'Standard'),
        }
        
        # Add optional fields if present
        if 'session_id' in response:
            enhanced['session_id'] = response['session_id']
        
        if 'duration' in response:
            enhanced['duration'] = response['duration']
        
        if 'orchestrator' in response:
            enhanced['orchestrator'] = response['orchestrator']
        
        # Add metadata about filtering
        enhanced['metadata'] = {
            'original_source_count': len(original_sources),
            'filtered_source_count': len(filtered_sources),
            'sources_removed': len(original_sources) - len(filtered_sources),
            'relevance_threshold': relevance_threshold
        }
        
        return enhanced
    
    @staticmethod
    def create_structured_answer_prompt(query: str, context: str) -> str:
        """
        Create an improved prompt for structured answer generation
        
        Args:
            query: User's question
            context: Legal context from retrieval
            
        Returns:
            Structured prompt for LLM
        """
        prompt = f"""You are an AI Legal Advisor for Pakistani law. Provide a clear, structured answer.

CRITICAL RULES:
1. ONLY use articles that are DIRECTLY relevant to the question
2. If an article is not relevant, DO NOT mention it
3. Be concise - avoid repetition
4. Focus on answering the actual question

ANSWER STRUCTURE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Your Question:** {query}

**Direct Answer:**
[Provide a clear, direct answer to the question in 2-3 sentences]

**Legal Basis:**
[Cite ONLY the relevant articles/sections that directly apply]

Example format:
• **Section X of [Law Name]:** [Brief explanation in simple words]
• **Article Y:** [How it applies to this situation]

**What This Means:**
[Explain in plain language what the law means for this situation]

**Practical Steps:**
[If applicable, suggest what actions can be taken]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Legal Context Available:**
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Important Notes:**
- Use simple language - explain as if to someone without legal knowledge
- Only cite articles that DIRECTLY answer the question
- If the context doesn't fully answer the question, say so clearly
- Keep your answer concise and focused

REMEMBER: Quality over quantity. Better to cite 2 relevant articles well than 10 articles poorly.

Now provide your structured answer:"""
        
        return prompt


# Example usage
if __name__ == "__main__":
    print("Response Formatter utility loaded")
    
    # Test filtering
    test_sources = [
        {'document': 'CrPC', 'article': '497', 'relevance_score': 3.5},
        {'document': 'CrPC', 'article': '54', 'relevance_score': -2.1},
        {'document': 'Muslim Law', 'article': '1', 'relevance_score': -4.7},
        {'document': 'Contract Act', 'article': '10', 'relevance_score': 0.8},
    ]
    
    filtered = ResponseFormatter.filter_relevant_sources(test_sources)
    print(f"\nFiltered {len(test_sources)} sources down to {len(filtered)}")
    for src in filtered:
        print(f"  - {src['document']} Article {src['article']} (Score: {src['relevance_score']})")
