"""
Presidio Internal Research Agent
A comprehensive LangChain agent with MCP, RAG, and Web Search capabilities
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.prompts import ChatPromptTemplate
    from langchain_aws import ChatBedrock
    from langchain.tools import Tool
    from langchain_community.tools import DuckDuckGoSearchRun
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.document_loaders import DirectoryLoader, TextLoader
    from langchain.schema import Document
    import boto3
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ LangChain dependencies not fully available: {e}")
    print("Please install dependencies with: pip install -r requirements.txt")
    LANGCHAIN_AVAILABLE = False
    
    # Mock classes for demonstration
    class ChatBedrock:
        def __init__(self, **kwargs): pass
    class Tool:
        def __init__(self, **kwargs): 
            self.name = kwargs.get('name', 'mock_tool')
            self.description = kwargs.get('description', 'Mock tool')
            self.func = kwargs.get('func', lambda x: f"Mock response for: {x}")
    class AgentExecutor:
        def __init__(self, **kwargs): pass
        def invoke(self, inputs): return {"output": "Mock agent response - please install dependencies"}

import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PresidioResearchAgent:
    """
    Main agent class that orchestrates MCP, RAG, and Web Search tools
    """
    
    def __init__(self):
        self.llm = None
        self.agent_executor = None
        self.vector_store = None
        self.embeddings = None
        self.mcp_toolkit = None
        self.tools = []
        
        # Initialize components
        self._setup_llm()
        self._setup_embeddings()
        self._setup_vector_store()
        self._setup_tools()
        self._setup_agent()
    
    def _setup_llm(self):
        """Initialize the language model with AWS Bedrock"""
        # Check for AWS credentials
        aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        try:
            # Initialize Bedrock client
            self.llm = ChatBedrock(
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                region_name=aws_region,
                model_kwargs={
                    "temperature": 0.1,
                    "max_tokens": 4000
                }
            )
            logger.info("✅ AWS Bedrock LLM initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock: {e}")
            # Fallback to mock for testing
            logger.warning("Using mock LLM for testing")
            self.llm = None
    
    def _setup_embeddings(self):
        """Initialize embeddings for RAG"""
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        logger.info("✅ Embeddings initialized")
    
    def _setup_vector_store(self):
        """Initialize or load the vector store for RAG"""
        persist_directory = "Week-4/presidio-research-agent/rag-system/chroma_db"
        
        # Create directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        try:
            # Try to load existing vector store
            self.vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
            
            # Check if vector store has documents
            if self.vector_store._collection.count() == 0:
                logger.info("Vector store is empty, will need to populate with documents")
            else:
                logger.info(f"✅ Vector store loaded with {self.vector_store._collection.count()} documents")
                
        except Exception as e:
            logger.warning(f"Could not load existing vector store: {e}")
            self.vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
    
    def populate_vector_store(self, documents_path: str = "Week-4/presidio-research-agent/data/hr-policies"):
        """
        Populate the vector store with HR policy documents
        """
        if not os.path.exists(documents_path):
            logger.warning(f"Documents path {documents_path} does not exist. Creating sample documents.")
            self._create_sample_hr_documents(documents_path)
        
        # Load documents
        from langchain_community.document_loaders import DirectoryLoader, TextLoader
        loader = DirectoryLoader(
            documents_path,
            glob="**/*.txt",
            loader_cls=TextLoader,
            loader_kwargs={'encoding': 'utf-8'},
            show_progress=True
        )
        
        try:
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} documents")
            
            if not documents:
                logger.warning("No documents found to load")
                return
            
            # Split documents
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            
            splits = text_splitter.split_documents(documents)
            logger.info(f"Split into {len(splits)} chunks")
            
            # Add to vector store
            self.vector_store.add_documents(splits)
            self.vector_store.persist()
            
            logger.info("✅ Vector store populated successfully")
            
        except Exception as e:
            logger.error(f"Error populating vector store: {e}")
            raise
    
    def _create_sample_hr_documents(self, documents_path: str):
        """Create sample HR policy documents for demonstration"""
        Path(documents_path).mkdir(parents=True, exist_ok=True)
        
        sample_docs = {
            "hiring_policy.txt": """
PRESIDIO HIRING POLICY

1. RECRUITMENT PROCESS
- All positions must be posted internally for 5 business days before external posting
- Hiring managers must complete diversity and inclusion training
- Background checks required for all positions
- Reference checks mandatory for senior roles

2. INTERVIEW PROCESS
- Structured interviews with standardized questions
- Panel interviews for management positions
- Skills assessments for technical roles
- Cultural fit evaluation required

3. COMPENSATION GUIDELINES
- Salary bands established for all positions
- Annual compensation review process
- Performance-based bonuses available
- Equity participation for senior roles

4. ONBOARDING REQUIREMENTS
- 30-day onboarding program for all new hires
- Buddy system assignment
- IT setup and security training
- Department-specific orientation

Last Updated: January 2024
            """,
            
            "ai_data_handling_policy.txt": """
PRESIDIO AI DATA HANDLING AND COMPLIANCE POLICY

1. DATA GOVERNANCE
- All AI systems must comply with GDPR, CCPA, and industry regulations
- Data minimization principles apply to all AI training datasets
- Regular audits of AI model performance and bias detection
- Data retention policies strictly enforced

2. AI MODEL DEVELOPMENT
- Ethical AI guidelines must be followed
- Model explainability requirements for customer-facing applications
- Regular bias testing and mitigation strategies
- Version control and model lineage tracking

3. CUSTOMER DATA PROTECTION
- Encryption at rest and in transit for all customer data
- Access controls and audit logging for AI systems
- Customer consent required for AI processing
- Right to explanation for automated decisions

4. COMPLIANCE MONITORING
- Monthly compliance reviews
- Incident response procedures for data breaches
- Regular training on AI ethics and data protection
- Third-party vendor assessments

Last Updated: December 2023
            """,
            
            "remote_work_policy.txt": """
PRESIDIO REMOTE WORK POLICY

1. ELIGIBILITY
- All full-time employees eligible after 90-day probation
- Manager approval required
- Role suitability assessment
- Home office setup requirements

2. WORK ARRANGEMENTS
- Hybrid model: minimum 2 days in office per week
- Core collaboration hours: 10 AM - 3 PM local time
- Flexible scheduling within business hours
- Regular check-ins with manager

3. TECHNOLOGY AND SECURITY
- Company-provided equipment mandatory
- VPN access required for all remote connections
- Security training completion required
- Regular security updates and patches

4. PERFORMANCE EXPECTATIONS
- Same productivity standards as in-office work
- Regular communication with team members
- Participation in virtual meetings and collaboration
- Quarterly performance reviews

Last Updated: March 2024
            """,
            
            "customer_feedback_analysis.txt": """
PRESIDIO Q1 2024 CUSTOMER FEEDBACK ANALYSIS

MARKETING CAMPAIGN FEEDBACK:

1. DIGITAL ADVERTISING CAMPAIGN
- 78% positive sentiment on social media ads
- Conversion rate: 3.2% (above industry average of 2.1%)
- Top performing channels: LinkedIn (4.1%), Google Ads (3.8%)
- Customer complaints: 12% found ads too frequent

2. EMAIL MARKETING
- Open rate: 24.5% (industry average: 21.3%)
- Click-through rate: 4.2%
- Unsubscribe rate: 0.8%
- Feedback: Customers want more personalized content

3. CONTENT MARKETING
- Blog engagement up 45% from Q4 2023
- Video content performed 60% better than text-only
- Customer requests: More case studies and tutorials
- SEO improvements led to 35% increase in organic traffic

4. TRADE SHOWS AND EVENTS
- Lead quality score: 8.2/10
- Follow-up conversion rate: 15%
- Customer feedback: Excellent booth presentation
- Suggestion: More interactive demos

OVERALL Q1 MARKETING PERFORMANCE:
- Customer acquisition cost decreased by 18%
- Brand awareness increased by 22%
- Customer satisfaction with marketing touchpoints: 4.3/5

Last Updated: April 2024
            """
        }
        
        for filename, content in sample_docs.items():
            with open(os.path.join(documents_path, filename), 'w', encoding='utf-8') as f:
                f.write(content.strip())
        
        logger.info(f"✅ Created {len(sample_docs)} sample HR documents")
    
    def _setup_tools(self):
        """Initialize all tools: MCP, RAG, and Web Search"""
        
        # 1. MCP Tool for Google Docs
        try:
            # Try to use the real MCP tool
            mcp_tool = self._create_real_mcp_tool()
            self.tools.append(mcp_tool)
            logger.info("✅ MCP Google Docs tool initialized")
        except Exception as e:
            logger.warning(f"MCP tools not available: {e}")
            # Create a fallback MCP tool
            self.tools.append(self._create_fallback_mcp_tool())
        
        # 2. RAG Tool for HR Policies
        rag_tool = Tool(
            name="search_hr_policies",
            description="Search through Presidio's HR policies and internal documents. Use this for questions about company policies, procedures, compliance, hiring, remote work, AI data handling, etc.",
            func=self._search_hr_policies
        )
        self.tools.append(rag_tool)
        
        # 3. Web Search Tool for Industry Benchmarks
        web_search = DuckDuckGoSearchRun()
        web_search_tool = Tool(
            name="web_search",
            description="Search the web for industry benchmarks, trends, regulatory updates, and external information. Use this for competitive analysis, market research, and current industry data.",
            func=web_search.run
        )
        self.tools.append(web_search_tool)
        
        # 4. Enhanced Web Search for Industry Analysis
        industry_search_tool = Tool(
            name="industry_benchmark_search",
            description="Specialized search for industry benchmarks, hiring trends, and competitive analysis. Provides structured data about market conditions and industry standards.",
            func=self._industry_benchmark_search
        )
        self.tools.append(industry_search_tool)
        
        logger.info(f"✅ Initialized {len(self.tools)} tools")
    
    def _create_real_mcp_tool(self):
        """Create the real MCP tool for Google Docs integration"""
        try:
            # Import the MCP client
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from mcp_client import SimpleMCPClient
            
            # Initialize the MCP client
            mcp_client = SimpleMCPClient("mcp-server")
            
            def google_docs_search(query: str) -> str:
                try:
                    result = mcp_client.search_google_docs(query)
                    if result and not result.startswith("Error"):
                        return f"Google Docs Search Results for: '{query}'\n\n{result}"
                    else:
                        return f"Google Docs search completed but no results found for: '{query}'\n\nNote: Make sure you have Google Docs in your Drive that match the search terms."
                except Exception as e:
                    logger.error(f"MCP Google Docs search failed: {e}")
                    return f"Error searching Google Docs: {str(e)}\n\nNote: Please ensure the MCP server is properly configured with Google credentials."
            
            return Tool(
                name="search_google_docs",
                description="Search Google Docs for insurance-related queries and company documents. Use this for accessing specific company documents, insurance procedures, and internal knowledge base.",
                func=google_docs_search
            )
            
        except Exception as e:
            logger.warning(f"Failed to initialize real MCP tool: {e}")
            return self._create_fallback_mcp_tool()
    
    def _create_fallback_mcp_tool(self):
        """Create a fallback MCP tool when the real one is not available"""
        def fallback_google_docs_search(query: str) -> str:
            return f"""
Google Docs Search Results for: "{query}"

⚠️ MCP Server Status: Using fallback mode

The Google Docs MCP server is configured but may need authentication.
To enable full Google Docs integration:

1. Ensure you have completed the OAuth flow
2. Check that token.json exists in data/google-docs-credentials/
3. Verify the MCP server can access your Google Drive

For now, here's what we would search for:
- Documents containing: "{query}"
- File types: Google Docs (.gdoc)
- Scope: Your accessible Google Drive files

To complete setup, run the MCP server authentication process.
            """
        
        return Tool(
            name="search_google_docs",
            description="Search Google Docs for insurance-related queries and company documents. Use this for accessing specific company documents, insurance procedures, and internal knowledge base.",
            func=fallback_google_docs_search
        )
    
    def _search_hr_policies(self, query: str) -> str:
        """Search HR policies using RAG"""
        try:
            if not self.vector_store:
                return "Vector store not initialized. Please populate with HR documents first."
            
            # Perform similarity search
            docs = self.vector_store.similarity_search(query, k=3)
            
            if not docs:
                return f"No relevant HR policy documents found for query: {query}"
            
            # Format results
            results = []
            for i, doc in enumerate(docs, 1):
                content = doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content
                source = doc.metadata.get('source', 'Unknown')
                results.append(f"{i}. Source: {source}\nContent: {content}\n")
            
            return f"Found {len(docs)} relevant HR policy documents:\n\n" + "\n".join(results)
            
        except Exception as e:
            logger.error(f"Error searching HR policies: {e}")
            return f"Error searching HR policies: {str(e)}"
    
    def _industry_benchmark_search(self, query: str) -> str:
        """Enhanced web search for industry benchmarks and trends"""
        try:
            # Use DuckDuckGo for basic search
            search = DuckDuckGoSearchRun()
            
            # Enhance query for better industry results
            enhanced_queries = [
                f"{query} industry benchmark 2024",
                f"{query} market trends statistics",
                f"{query} industry report analysis"
            ]
            
            results = []
            for enhanced_query in enhanced_queries[:2]:  # Limit to 2 searches
                try:
                    result = search.run(enhanced_query)
                    results.append(f"Search: {enhanced_query}\nResults: {result}\n")
                except Exception as e:
                    logger.warning(f"Search failed for {enhanced_query}: {e}")
            
            if not results:
                return f"No industry benchmark data found for: {query}"
            
            return f"Industry Benchmark Analysis for '{query}':\n\n" + "\n".join(results)
            
        except Exception as e:
            logger.error(f"Error in industry benchmark search: {e}")
            return f"Error searching industry benchmarks: {str(e)}"
    
    def _setup_agent(self):
        """Initialize the LangChain agent"""
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are Presidio's Internal Research Agent, designed to help employees with accurate, contextual, and actionable responses.

You have access to three specialized tools:

1. **Google Docs Search** (search_google_docs): Access company documents, insurance procedures, and internal knowledge base
2. **HR Policy Search** (search_hr_policies): Search through HR policies, compliance documents, and internal procedures  
3. **Web Search** (web_search): Find industry benchmarks, trends, and external information
4. **Industry Benchmark Search** (industry_benchmark_search): Specialized search for market data and competitive analysis

**Guidelines:**
- Always provide accurate, well-sourced information
- Use multiple tools when needed to give comprehensive answers
- Cite your sources clearly
- For policy questions, prioritize internal HR documents
- For industry data, use web search tools
- For company-specific documents, use Google Docs search
- Be concise but thorough in your responses
- If you cannot find specific information, clearly state this

**Response Format:**
- Start with a brief summary
- Provide detailed findings with sources
- Include actionable recommendations when appropriate
- End with suggestions for follow-up if needed

Current date: {current_date}
"""),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Create the agent
        if self.llm:
            agent = create_tool_calling_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
        else:
            # Mock agent for testing without LLM
            agent = None
        
        # Create the agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
        
        logger.info("✅ Agent initialized successfully")
    
    async def query(self, question: str) -> str:
        """
        Process a query using the research agent
        """
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            response = await self.agent_executor.ainvoke({
                "input": question,
                "current_date": current_date
            })
            
            return response["output"]
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error while processing your query: {str(e)}"
    
    def query_sync(self, question: str) -> str:
        """
        Synchronous version of query method
        """
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            response = self.agent_executor.invoke({
                "input": question,
                "current_date": current_date
            })
            
            return response["output"]
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error while processing your query: {str(e)}"

def main():
    """
    Main function to demonstrate the agent
    """
    print("🚀 Initializing Presidio Research Agent...")
    
    try:
        # Initialize the agent
        agent = PresidioResearchAgent()
        
        # Populate vector store with HR documents
        print("📚 Populating vector store with HR policies...")
        agent.populate_vector_store()
        
        print("\n✅ Presidio Research Agent is ready!")
        print("\nExample queries you can try:")
        print("1. 'Summarize all customer feedback related to our Q1 marketing campaigns.'")
        print("2. 'Compare our current hiring trend with industry benchmarks.'")
        print("3. 'Find relevant compliance policies related to AI data handling.'")
        print("4. 'What are our remote work policies?'")
        print("5. 'Search for insurance claim processing procedures.'")
        
        # Interactive mode
        print("\n" + "="*60)
        print("INTERACTIVE MODE - Type 'quit' to exit")
        print("="*60)
        
        while True:
            try:
                question = input("\n🤔 Your question: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not question:
                    continue
                
                print(f"\n🔍 Processing: {question}")
                print("-" * 50)
                
                response = agent.query_sync(question)
                print(f"\n📋 Response:\n{response}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
