"""
Enhanced Web Search Tools for Industry Benchmarks and Trends
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from urllib.parse import urlencode, quote_plus

logger = logging.getLogger(__name__)

class IndustryBenchmarkSearcher:
    """
    Specialized web search tool for industry benchmarks, hiring trends, and competitive analysis
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_hiring_trends(self, query: str) -> Dict[str, Any]:
        """
        Search for hiring trends and employment statistics
        """
        try:
            # Enhanced search terms for hiring trends
            search_terms = [
                f"{query} hiring trends 2024",
                f"{query} employment statistics",
                f"{query} job market analysis",
                f"{query} recruitment benchmarks"
            ]
            
            results = []
            for term in search_terms[:2]:  # Limit searches
                search_result = self._perform_search(term)
                if search_result:
                    results.append({
                        'query': term,
                        'results': search_result
                    })
            
            return {
                'category': 'hiring_trends',
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'summary': self._generate_hiring_summary(results)
            }
            
        except Exception as e:
            logger.error(f"Error searching hiring trends: {e}")
            return {
                'category': 'hiring_trends',
                'query': query,
                'error': str(e),
                'results': []
            }
    
    def search_industry_benchmarks(self, industry: str, metric: str) -> Dict[str, Any]:
        """
        Search for specific industry benchmarks and KPIs
        """
        try:
            search_terms = [
                f"{industry} {metric} benchmark 2024",
                f"{industry} industry standards {metric}",
                f"{metric} average {industry} sector"
            ]
            
            results = []
            for term in search_terms[:2]:
                search_result = self._perform_search(term)
                if search_result:
                    results.append({
                        'query': term,
                        'results': search_result
                    })
            
            return {
                'category': 'industry_benchmarks',
                'industry': industry,
                'metric': metric,
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'summary': self._generate_benchmark_summary(results, industry, metric)
            }
            
        except Exception as e:
            logger.error(f"Error searching industry benchmarks: {e}")
            return {
                'category': 'industry_benchmarks',
                'industry': industry,
                'metric': metric,
                'error': str(e),
                'results': []
            }
    
    def search_regulatory_updates(self, domain: str) -> Dict[str, Any]:
        """
        Search for regulatory updates and compliance information
        """
        try:
            search_terms = [
                f"{domain} regulatory updates 2024",
                f"{domain} compliance requirements",
                f"{domain} new regulations",
                f"{domain} policy changes"
            ]
            
            results = []
            for term in search_terms[:2]:
                search_result = self._perform_search(term)
                if search_result:
                    results.append({
                        'query': term,
                        'results': search_result
                    })
            
            return {
                'category': 'regulatory_updates',
                'domain': domain,
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'summary': self._generate_regulatory_summary(results, domain)
            }
            
        except Exception as e:
            logger.error(f"Error searching regulatory updates: {e}")
            return {
                'category': 'regulatory_updates',
                'domain': domain,
                'error': str(e),
                'results': []
            }
    
    def _perform_search(self, query: str) -> Optional[str]:
        """
        Perform a web search using DuckDuckGo
        """
        try:
            # Use DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant information
            result_text = ""
            
            if data.get('Abstract'):
                result_text += f"Summary: {data['Abstract']}\n"
            
            if data.get('RelatedTopics'):
                result_text += "\nRelated Information:\n"
                for topic in data['RelatedTopics'][:3]:  # Limit to 3 topics
                    if isinstance(topic, dict) and topic.get('Text'):
                        result_text += f"- {topic['Text']}\n"
            
            if data.get('Results'):
                result_text += "\nKey Results:\n"
                for result in data['Results'][:3]:  # Limit to 3 results
                    if result.get('Text'):
                        result_text += f"- {result['Text']}\n"
            
            return result_text if result_text.strip() else None
            
        except Exception as e:
            logger.warning(f"Search failed for query '{query}': {e}")
            return None
    
    def _generate_hiring_summary(self, results: List[Dict]) -> str:
        """
        Generate a summary of hiring trends from search results
        """
        if not results:
            return "No hiring trend data available."
        
        summary = "HIRING TRENDS SUMMARY:\n\n"
        
        # Extract key insights from results
        key_points = []
        for result in results:
            if result.get('results'):
                # Simple keyword extraction for trends
                text = result['results'].lower()
                if 'increase' in text or 'growth' in text:
                    key_points.append("• Positive hiring growth indicated")
                if 'decrease' in text or 'decline' in text:
                    key_points.append("• Hiring decline trends noted")
                if 'remote' in text:
                    key_points.append("• Remote work trends affecting hiring")
                if 'skill' in text:
                    key_points.append("• Skills-based hiring emphasis")
        
        if key_points:
            summary += "\n".join(set(key_points))  # Remove duplicates
        else:
            summary += "General hiring market information found, but specific trends require deeper analysis."
        
        return summary
    
    def _generate_benchmark_summary(self, results: List[Dict], industry: str, metric: str) -> str:
        """
        Generate a summary of industry benchmarks
        """
        if not results:
            return f"No benchmark data available for {metric} in {industry} industry."
        
        summary = f"INDUSTRY BENCHMARK SUMMARY - {industry.upper()} {metric.upper()}:\n\n"
        
        # Extract numerical data if possible
        numbers = []
        for result in results:
            if result.get('results'):
                text = result['results']
                # Simple regex to find percentages and numbers
                percentages = re.findall(r'(\d+(?:\.\d+)?%)', text)
                numbers.extend(percentages)
        
        if numbers:
            summary += f"Key Metrics Found: {', '.join(numbers[:5])}\n"
        
        summary += f"Industry benchmark data for {metric} in {industry} sector available in search results."
        
        return summary
    
    def _generate_regulatory_summary(self, results: List[Dict], domain: str) -> str:
        """
        Generate a summary of regulatory updates
        """
        if not results:
            return f"No regulatory updates found for {domain}."
        
        summary = f"REGULATORY UPDATES SUMMARY - {domain.upper()}:\n\n"
        
        # Look for key regulatory terms
        key_terms = ['compliance', 'regulation', 'requirement', 'policy', 'law', 'guideline']
        found_terms = []
        
        for result in results:
            if result.get('results'):
                text = result['results'].lower()
                for term in key_terms:
                    if term in text and term not in found_terms:
                        found_terms.append(term)
        
        if found_terms:
            summary += f"Key Areas: {', '.join(found_terms).title()}\n"
        
        summary += f"Regulatory information for {domain} domain found in search results."
        
        return summary

class CompetitiveAnalysisSearcher:
    """
    Tool for competitive analysis and market research
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def analyze_competitor_trends(self, company: str, industry: str) -> Dict[str, Any]:
        """
        Analyze competitor trends and market positioning
        """
        try:
            search_terms = [
                f"{company} competitors {industry}",
                f"{industry} market leaders",
                f"{company} market share {industry}"
            ]
            
            results = []
            for term in search_terms:
                # Simulate competitive analysis results
                results.append({
                    'query': term,
                    'analysis': f"Competitive analysis for {term} - market research data would be gathered here"
                })
            
            return {
                'category': 'competitive_analysis',
                'company': company,
                'industry': industry,
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'recommendations': self._generate_competitive_recommendations(company, industry)
            }
            
        except Exception as e:
            logger.error(f"Error in competitive analysis: {e}")
            return {
                'category': 'competitive_analysis',
                'company': company,
                'industry': industry,
                'error': str(e),
                'results': []
            }
    
    def _generate_competitive_recommendations(self, company: str, industry: str) -> List[str]:
        """
        Generate competitive analysis recommendations
        """
        return [
            f"Monitor {industry} industry trends regularly",
            f"Benchmark {company} performance against market leaders",
            "Focus on differentiation strategies",
            "Track competitor pricing and positioning",
            "Identify market gaps and opportunities"
        ]

# Factory function to create search tools
def create_web_search_tools() -> Dict[str, Any]:
    """
    Create and return web search tools for the agent
    """
    benchmark_searcher = IndustryBenchmarkSearcher()
    competitive_searcher = CompetitiveAnalysisSearcher()
    
    return {
        'benchmark_searcher': benchmark_searcher,
        'competitive_searcher': competitive_searcher,
        'search_functions': {
            'hiring_trends': benchmark_searcher.search_hiring_trends,
            'industry_benchmarks': benchmark_searcher.search_industry_benchmarks,
            'regulatory_updates': benchmark_searcher.search_regulatory_updates,
            'competitive_analysis': competitive_searcher.analyze_competitor_trends
        }
    }
