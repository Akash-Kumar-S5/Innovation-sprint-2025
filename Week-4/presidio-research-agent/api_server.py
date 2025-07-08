"""
FastAPI Server for Presidio Research Agent
Provides REST API endpoints for the LangChain agent
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncio
import logging
import os
import sys
from datetime import datetime
import uvicorn

# Add the agent-core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'agent-core'))

try:
    from main import PresidioResearchAgent
except ImportError:
    # Add the agent-core directory to the path
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'agent-core'))
    from main import PresidioResearchAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Presidio Research Agent API",
    description="Internal Research Agent with MCP, RAG, and Web Search capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
research_agent: Optional[PresidioResearchAgent] = None

# Pydantic models for API requests/responses
class QueryRequest(BaseModel):
    question: str = Field(..., description="The question to ask the research agent")
    context: Optional[str] = Field(None, description="Additional context for the query")

class QueryResponse(BaseModel):
    answer: str = Field(..., description="The agent's response")
    timestamp: str = Field(..., description="When the query was processed")
    processing_time: Optional[float] = Field(None, description="Time taken to process the query in seconds")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    timestamp: str = Field(..., description="Current timestamp")
    agent_ready: bool = Field(..., description="Whether the research agent is ready")
    components: Dict[str, bool] = Field(..., description="Status of individual components")

class ToolsResponse(BaseModel):
    tools: List[Dict[str, Any]] = Field(..., description="Available tools and their descriptions")
    count: int = Field(..., description="Number of available tools")

class VectorStoreRequest(BaseModel):
    documents_path: Optional[str] = Field(None, description="Path to documents to index")
    force_rebuild: bool = Field(False, description="Whether to rebuild the vector store")

class VectorStoreResponse(BaseModel):
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    document_count: Optional[int] = Field(None, description="Number of documents processed")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the research agent on startup"""
    global research_agent
    
    try:
        logger.info("🚀 Starting Presidio Research Agent API...")
        
        # Initialize the agent
        research_agent = PresidioResearchAgent()
        
        # Populate vector store with sample documents
        logger.info("📚 Populating vector store...")
        research_agent.populate_vector_store()
        
        logger.info("✅ Presidio Research Agent API is ready!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize research agent: {e}")
        # Don't fail startup, but log the error
        research_agent = None

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check the health status of the API and its components"""
    
    components = {
        "agent_initialized": research_agent is not None,
        "vector_store": False,
        "llm": False,
        "tools": False
    }
    
    if research_agent:
        try:
            components["vector_store"] = research_agent.vector_store is not None
            components["llm"] = research_agent.llm is not None
            components["tools"] = len(research_agent.tools) > 0
        except Exception as e:
            logger.warning(f"Error checking components: {e}")
    
    agent_ready = all(components.values())
    status = "healthy" if agent_ready else "degraded"
    
    return HealthResponse(
        status=status,
        timestamp=datetime.now().isoformat(),
        agent_ready=agent_ready,
        components=components
    )

# Main query endpoint
@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Send a query to the research agent and get a response
    """
    if not research_agent:
        raise HTTPException(
            status_code=503,
            detail="Research agent is not initialized. Please check the service health."
        )
    
    try:
        start_time = datetime.now()
        
        # Process the query
        question = request.question
        if request.context:
            question = f"Context: {request.context}\n\nQuestion: {question}"
        
        logger.info(f"Processing query: {request.question}")
        
        # Use the synchronous version for the API
        response = research_agent.query_sync(question)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Query processed in {processing_time:.2f} seconds")
        
        return QueryResponse(
            answer=response,
            timestamp=end_time.isoformat(),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

# Tools information endpoint
@app.get("/tools", response_model=ToolsResponse)
async def get_tools():
    """
    Get information about available tools
    """
    if not research_agent:
        raise HTTPException(
            status_code=503,
            detail="Research agent is not initialized."
        )
    
    try:
        tools_info = []
        
        for tool in research_agent.tools:
            tool_info = {
                "name": tool.name,
                "description": tool.description,
                "type": type(tool).__name__
            }
            tools_info.append(tool_info)
        
        return ToolsResponse(
            tools=tools_info,
            count=len(tools_info)
        )
        
    except Exception as e:
        logger.error(f"Error getting tools info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tools information: {str(e)}"
        )

# Vector store management endpoint
@app.post("/vector-store/rebuild", response_model=VectorStoreResponse)
async def rebuild_vector_store(request: VectorStoreRequest):
    """
    Rebuild the vector store with documents
    """
    if not research_agent:
        raise HTTPException(
            status_code=503,
            detail="Research agent is not initialized."
        )
    
    try:
        logger.info("Rebuilding vector store...")
        
        documents_path = request.documents_path or "Week-4/presidio-research-agent/data/hr-policies"
        
        # Rebuild the vector store
        research_agent.populate_vector_store(documents_path)
        
        # Get document count
        doc_count = 0
        if research_agent.vector_store:
            try:
                doc_count = research_agent.vector_store._collection.count()
            except:
                doc_count = None
        
        return VectorStoreResponse(
            status="success",
            message="Vector store rebuilt successfully",
            document_count=doc_count
        )
        
    except Exception as e:
        logger.error(f"Error rebuilding vector store: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error rebuilding vector store: {str(e)}"
        )

# Example queries endpoint
@app.get("/examples")
async def get_example_queries():
    """
    Get example queries that can be used with the research agent
    """
    examples = [
        {
            "category": "Customer Feedback",
            "query": "Summarize all customer feedback related to our Q1 marketing campaigns.",
            "description": "Analyzes customer feedback data from internal documents"
        },
        {
            "category": "Industry Benchmarks",
            "query": "Compare our current hiring trend with industry benchmarks.",
            "description": "Uses web search to find industry hiring data and compares with internal policies"
        },
        {
            "category": "Compliance",
            "query": "Find relevant compliance policies related to AI data handling.",
            "description": "Searches HR policies and regulatory information for AI compliance"
        },
        {
            "category": "HR Policies",
            "query": "What are our remote work policies?",
            "description": "Retrieves information from internal HR policy documents"
        },
        {
            "category": "Insurance Procedures",
            "query": "Search for insurance claim processing procedures.",
            "description": "Uses Google Docs search to find insurance-related documents"
        },
        {
            "category": "Market Analysis",
            "query": "What are the latest trends in the insurance industry?",
            "description": "Performs web search for current industry trends and analysis"
        }
    ]
    
    return {
        "examples": examples,
        "count": len(examples),
        "usage": "Send any of these queries to the /query endpoint to see the agent in action"
    }

# Batch query endpoint
@app.post("/query/batch")
async def batch_query(queries: List[QueryRequest]):
    """
    Process multiple queries in batch
    """
    if not research_agent:
        raise HTTPException(
            status_code=503,
            detail="Research agent is not initialized."
        )
    
    if len(queries) > 10:  # Limit batch size
        raise HTTPException(
            status_code=400,
            detail="Batch size limited to 10 queries"
        )
    
    try:
        results = []
        
        for i, request in enumerate(queries):
            try:
                start_time = datetime.now()
                
                question = request.question
                if request.context:
                    question = f"Context: {request.context}\n\nQuestion: {question}"
                
                response = research_agent.query_sync(question)
                
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()
                
                results.append({
                    "index": i,
                    "query": request.question,
                    "answer": response,
                    "timestamp": end_time.isoformat(),
                    "processing_time": processing_time,
                    "status": "success"
                })
                
            except Exception as e:
                results.append({
                    "index": i,
                    "query": request.question,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "status": "error"
                })
        
        return {
            "results": results,
            "total_queries": len(queries),
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"])
        }
        
    except Exception as e:
        logger.error(f"Error processing batch queries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing batch queries: {str(e)}"
        )

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "service": "Presidio Research Agent API",
        "version": "1.0.0",
        "description": "Internal Research Agent with MCP, RAG, and Web Search capabilities",
        "endpoints": {
            "health": "/health - Check service health",
            "query": "/query - Send a query to the research agent",
            "tools": "/tools - Get information about available tools",
            "examples": "/examples - Get example queries",
            "docs": "/docs - Interactive API documentation",
            "vector_store": "/vector-store/rebuild - Rebuild the vector store"
        },
        "status": "ready" if research_agent else "initializing"
    }

def main():
    """
    Main function to run the FastAPI server
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Presidio Research Agent API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting Presidio Research Agent API on {args.host}:{args.port}")
    print(f"📚 Documentation available at http://{args.host}:{args.port}/docs")
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )

if __name__ == "__main__":
    main()
