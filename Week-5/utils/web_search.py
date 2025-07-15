import requests
from typing import Dict, Any, List
from duckduckgo_search import DDGS
import time

class WebSearchClient:
    """
    Real web search client using DuckDuckGo Search API.
    """
    
    def __init__(self):
        self.ddgs = DDGS()
    
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Perform web search using DuckDuckGo.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with search results
        """
        try:
            start_time = time.time()
            
            # Perform the search
            results = list(self.ddgs.text(query, max_results=max_results))
            
            search_time = time.time() - start_time
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("body", ""),
                    "url": result.get("href", "")
                })
            
            return {
                "results": formatted_results,
                "total_results": len(formatted_results),
                "search_time": round(search_time, 2),
                "query": query
            }
            
        except Exception as e:
            return {
                "results": [],
                "total_results": 0,
                "search_time": 0,
                "query": query,
                "error": str(e)
            }
    
    def search_with_context(self, query: str, context_keywords: List[str], max_results: int = 3) -> Dict[str, Any]:
        """
        Perform contextual web search by adding relevant keywords.
        
        Args:
            query: Original search query
            context_keywords: Additional keywords to add context
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with search results
        """
        # Enhance query with context
        enhanced_query = f"{query} {' '.join(context_keywords)}"
        return self.search(enhanced_query, max_results)
    
    def search_it_topics(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """
        Search for IT-related topics with relevant context.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            Dictionary with search results
        """
        it_context = ["IT support", "technical help", "enterprise", "corporate"]
        return self.search_with_context(query, it_context, max_results)
    
    def search_finance_topics(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """
        Search for Finance-related topics with relevant context.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            Dictionary with search results
        """
        finance_context = ["corporate finance", "business finance", "enterprise", "company policy"]
        return self.search_with_context(query, finance_context, max_results)
    
    def test_connection(self) -> bool:
        """
        Test the web search connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = self.search("test query", max_results=1)
            return result["total_results"] >= 0  # Even 0 results means connection works
        except Exception as e:
            print(f"Web search connection test failed: {str(e)}")
            return False