import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
import boto3

# Load environment variables
load_dotenv()

class BedrockClient:
    """
    LangChain-based AWS Bedrock client for LLM interactions.
    """
    
    def __init__(self):
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        # Initialize Bedrock client
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
        
        # Initialize LangChain Bedrock Chat
        self.llm = ChatBedrock(
            client=self.bedrock_client,
            model_id=self.model_id,
            model_kwargs={
                "max_tokens": 2000,
                "temperature": 0.3,
                "top_p": 0.9
            }
        )
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        Use Claude to classify a query as IT or Finance.
        
        Args:
            query: The user's query string
            
        Returns:
            Dictionary with classification results
        """
        prompt = PromptTemplate(
            input_variables=["query"],
            template="""You are a query classification system. Classify the following query as either "IT" or "Finance" based on its content.

Query: {query}

Analyze the query and respond with a JSON object containing:
- "category": either "IT" or "Finance"
- "confidence": a float between 0.0 and 1.0
- "reasoning": a brief explanation of why you chose this category

IT queries typically involve: technology, software, hardware, networks, passwords, systems, applications, security, troubleshooting, VPN, laptops, servers, email, printers, wifi, technical support.

Finance queries typically involve: budget, expenses, reimbursement, payroll, salary, invoices, payments, accounting, taxes, financial reports, billing, receipts, procurement, purchasing, contracts.

Respond only with the JSON object, no additional text."""
        )
        
        formatted_prompt = prompt.format(query=query)
        
        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=formatted_prompt)])
            # Parse the JSON response
            import json
            result = json.loads(response.content.strip())
            return result
        except Exception as e:
            # Fallback classification
            return {
                "category": "IT",
                "confidence": 0.5,
                "reasoning": f"Error in classification: {str(e)}, defaulting to IT"
            }
    
    def generate_response(self, query: str, context: str, agent_type: str) -> str:
        """
        Generate a response using Claude based on query and context.
        
        Args:
            query: The user's query
            context: Relevant context information
            agent_type: Either "IT" or "Finance"
            
        Returns:
            Generated response string
        """
        prompt = PromptTemplate(
            input_variables=["query", "context", "agent_type"],
            template="""You are a helpful {agent_type} support agent. Answer the user's query based on the provided context.

Context:
{context}

User Query: {query}

Instructions:
- Be helpful and professional
- Use the context to provide accurate information
- If the context doesn't contain the answer, acknowledge this and provide general guidance
- Keep responses clear and actionable
- For IT queries: focus on technical solutions, procedures, and support contacts
- For Finance queries: focus on policies, procedures, and financial processes

Response:"""
        )
        
        formatted_prompt = prompt.format(
            query=query,
            context=context,
            agent_type=agent_type
        )
        
        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=formatted_prompt)])
            return response.content.strip()
        except Exception as e:
            return f"I apologize, but I'm having trouble generating a response right now. Error: {str(e)}. Please contact support directly."
    
    def enhance_search_query(self, original_query: str, agent_type: str) -> str:
        """
        Enhance a search query for better web search results.
        
        Args:
            original_query: The original user query
            agent_type: Either "IT" or "Finance"
            
        Returns:
            Enhanced search query
        """
        prompt = PromptTemplate(
            input_variables=["query", "agent_type"],
            template="""Transform the following user query into an optimized web search query for {agent_type} information.

Original Query: {query}

Create a search query that:
- Uses relevant keywords for {agent_type} topics
- Is specific enough to find useful results
- Includes common industry terms
- Is suitable for web search engines

Respond with only the enhanced search query, no additional text."""
        )
        
        formatted_prompt = prompt.format(query=original_query, agent_type=agent_type)
        
        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=formatted_prompt)])
            return response.content.strip()
        except Exception as e:
            return original_query
    
    def test_connection(self) -> bool:
        """
        Test the connection to AWS Bedrock.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content="Hello, please respond with 'Connection successful'")])
            return "successful" in response.content.lower()
        except Exception as e:
            print(f"Bedrock connection test failed: {str(e)}")
            return False