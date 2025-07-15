#!/usr/bin/env python3
"""
Multi-Agent Support System using LangGraph
A supervisor architecture where a supervisor agent routes queries to specialized IT and Finance agents.
"""

import os
import sys
from typing import Dict, Any, List, Literal, TypedDict, Union
from datetime import datetime

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils'))

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel

from bedrock_client import BedrockClient
from web_search import WebSearchClient


class AgentState(TypedDict):
    """State shared across all agents in the workflow"""
    messages: List[Union[HumanMessage, AIMessage]]
    query: str
    category: str
    confidence: float
    reasoning: str
    answer: str
    sources: List[str]
    internal_docs: List[str]
    web_results: List[Dict[str, Any]]
    next_agent: str


class MultiAgentWorkflow:
    """
    LangGraph-based multi-agent workflow for IT and Finance support
    """
    
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.web_search_client = WebSearchClient()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("supervisor", self.supervisor_agent)
        workflow.add_node("it_agent", self.it_agent)
        workflow.add_node("finance_agent", self.finance_agent)
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "supervisor",
            self.route_decision,
            {
                "it_agent": "it_agent",
                "finance_agent": "finance_agent",
                "END": END
            }
        )
        workflow.add_edge("it_agent", END)
        workflow.add_edge("finance_agent", END)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        return workflow
    
    def supervisor_agent(self, state: AgentState) -> AgentState:
        """
        Supervisor agent that classifies queries and routes to appropriate specialist
        """
        query = state["query"]
        
        # Use Bedrock to classify the query
        classification = self.bedrock_client.classify_query(query)
        
        # Update state with classification results
        state["category"] = classification["category"]
        state["confidence"] = classification["confidence"]
        state["reasoning"] = classification["reasoning"]
        
        # Determine next agent
        if classification["category"] == "IT":
            state["next_agent"] = "it_agent"
        elif classification["category"] == "Finance":
            state["next_agent"] = "finance_agent"
        else:
            state["next_agent"] = "END"
        
        # Add supervisor message
        supervisor_msg = AIMessage(
            content=f"Query classified as {classification['category']} with {classification['confidence']:.2f} confidence. Routing to {state['next_agent']}."
        )
        state["messages"] = state["messages"] + [supervisor_msg]
        
        return state
    
    def route_decision(self, state: AgentState) -> str:
        """
        Routing logic for conditional edges
        """
        return state["next_agent"]
    
    def it_agent(self, state: AgentState) -> AgentState:
        """
        IT specialist agent that handles IT-related queries
        """
        query = state["query"]
        
        # Search internal IT documentation
        internal_results = self._search_internal_docs(query, "it")
        state["internal_docs"] = internal_results
        
        # Perform web search for IT topics
        try:
            enhanced_query = self.bedrock_client.enhance_search_query(query, "IT")
            web_results = self.web_search_client.search_it_topics(enhanced_query, max_results=3)
            state["web_results"] = web_results.get("results", [])
        except Exception as e:
            state["web_results"] = []
        
        # Collect sources
        sources = []
        context_parts = []
        
        if internal_results:
            sources.append("Internal IT Documentation")
            context_parts.extend(internal_results)
        
        if state["web_results"]:
            sources.append("Web Search")
            for result in state["web_results"]:
                context_parts.append(f"{result['title']}: {result['snippet']} (Source: {result['url']})")
        
        state["sources"] = sources
        
        # Generate response using Bedrock
        if context_parts:
            context = "\\n\\n".join(context_parts)
            try:
                answer = self.bedrock_client.generate_response(query, context, "IT")
            except Exception as e:
                answer = f"Based on available information:\\n\\n{context}\\n\\nFor additional support, contact helpdesk@company.com or call ext. 1234."
        else:
            answer = "I couldn't find specific information about your IT query. Please contact the IT helpdesk at helpdesk@company.com or call ext. 1234 for direct assistance."
        
        state["answer"] = answer
        
        # Add IT agent message
        it_msg = AIMessage(content=answer)
        state["messages"] = state["messages"] + [it_msg]
        
        return state
    
    def finance_agent(self, state: AgentState) -> AgentState:
        """
        Finance specialist agent that handles Finance-related queries
        """
        query = state["query"]
        
        # Search internal Finance documentation
        internal_results = self._search_internal_docs(query, "finance")
        state["internal_docs"] = internal_results
        
        # Perform web search for Finance topics
        try:
            enhanced_query = self.bedrock_client.enhance_search_query(query, "Finance")
            web_results = self.web_search_client.search_finance_topics(enhanced_query, max_results=3)
            state["web_results"] = web_results.get("results", [])
        except Exception as e:
            state["web_results"] = []
        
        # Collect sources
        sources = []
        context_parts = []
        
        if internal_results:
            sources.append("Internal Finance Documentation")
            context_parts.extend(internal_results)
        
        if state["web_results"]:
            sources.append("Web Search")
            for result in state["web_results"]:
                context_parts.append(f"{result['title']}: {result['snippet']} (Source: {result['url']})")
        
        state["sources"] = sources
        
        # Generate response using Bedrock
        if context_parts:
            context = "\\n\\n".join(context_parts)
            try:
                answer = self.bedrock_client.generate_response(query, context, "Finance")
            except Exception as e:
                answer = f"Based on available information:\\n\\n{context}\\n\\nFor additional support, contact finance@company.com or call ext. 5678."
        else:
            answer = "I couldn't find specific information about your Finance query. Please contact the Finance department at finance@company.com or call ext. 5678 for direct assistance."
        
        state["answer"] = answer
        
        # Add Finance agent message
        finance_msg = AIMessage(content=answer)
        state["messages"] = state["messages"] + [finance_msg]
        
        return state
    
    def _search_internal_docs(self, query: str, doc_type: str) -> List[str]:
        """
        Search through internal documentation files
        """
        results = []
        
        if doc_type == "it":
            docs_path = os.path.join(self.base_dir, "docs", "it")
            doc_files = [
                "vpn_setup.txt",
                "software_approval.txt", 
                "hardware_requests.txt",
                "troubleshooting.txt",
                "security_policies.txt"
            ]
        elif doc_type == "finance":
            docs_path = os.path.join(self.base_dir, "docs", "finance")
            doc_files = [
                "reimbursement_policy.txt",
                "budget_procedures.txt",
                "payroll_info.txt",
                "expense_guidelines.txt",
                "financial_reports.txt"
            ]
        else:
            return results
        
        for doc_file in doc_files:
            try:
                file_path = os.path.join(docs_path, doc_file)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    if query.lower() in content.lower():
                        # Extract relevant section
                        lines = content.split('\\n')
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower():
                                context = ' '.join(lines[max(0, i-1):i+3])
                                results.append(f"From {doc_file}: {context[:200]}...")
                                break
            except FileNotFoundError:
                continue
            except Exception as e:
                continue
        
        return results
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent workflow
        """
        # Initialize state
        initial_state = AgentState(
            messages=[HumanMessage(content=query)],
            query=query,
            category="",
            confidence=0.0,
            reasoning="",
            answer="",
            sources=[],
            internal_docs=[],
            web_results=[],
            next_agent=""
        )
        
        # Run the workflow
        result = self.app.invoke(initial_state)
        
        # Format response
        return {
            "query": query,
            "classification": {
                "category": result["category"],
                "confidence": result["confidence"],
                "reasoning": result["reasoning"]
            },
            "answer": result["answer"],
            "sources": result["sources"],
            "internal_docs": result["internal_docs"],
            "web_results": result["web_results"],
            "messages": [msg.content for msg in result["messages"]],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """
        Get information about the workflow structure
        """
        return {
            "framework": "LangGraph",
            "architecture": "Supervisor with Specialized Agents",
            "agents": {
                "supervisor": {
                    "role": "Query classification and routing",
                    "capabilities": ["Claude-powered classification", "Intelligent routing"]
                },
                "it_agent": {
                    "role": "IT support specialist",
                    "capabilities": ["Internal docs search", "Web search", "Technical guidance"]
                },
                "finance_agent": {
                    "role": "Finance support specialist", 
                    "capabilities": ["Internal docs search", "Web search", "Financial guidance"]
                }
            },
            "workflow_steps": [
                "1. Supervisor classifies query",
                "2. Routes to appropriate specialist",
                "3. Specialist searches internal docs",
                "4. Specialist performs web search",
                "5. Specialist generates contextual response"
            ],
            "features": [
                "State management across agents",
                "Conditional routing",
                "Real-time web search",
                "Internal documentation integration",
                "AWS Bedrock LLM integration"
            ]
        }


def main():
    """
    Main function to run the LangGraph multi-agent workflow interactively
    """
    print("="*70)
    print("🤖 LangGraph Multi-Agent Support System")
    print("="*70)
    print()
    
    # Initialize workflow
    workflow = MultiAgentWorkflow()
    
    # Test connections
    print("Testing system connections...")
    try:
        bedrock_ok = workflow.bedrock_client.test_connection()
        web_ok = workflow.web_search_client.test_connection()
        
        print(f"✓ AWS Bedrock: {'OK' if bedrock_ok else 'FAILED'}")
        print(f"✓ Web Search: {'OK' if web_ok else 'FAILED'}")
        
        if not (bedrock_ok and web_ok):
            print("❌ Connection failed. Please check your .env file and credentials.")
            return
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return
    
    # Display workflow info
    workflow_info = workflow.get_workflow_info()
    print(f"\\n🔧 Framework: {workflow_info['framework']}")
    print(f"🏗️  Architecture: {workflow_info['architecture']}")
    print()
    
    print("🤖 Available Agents:")
    for agent_name, agent_info in workflow_info['agents'].items():
        print(f"   • {agent_name}: {agent_info['role']}")
    print()
    
    print("🔄 Workflow Process:")
    for step in workflow_info['workflow_steps']:
        print(f"   {step}")
    print()
    
    # Interactive mode
    print("💬 Interactive Mode - Enter your queries (type 'quit' to exit):")
    print("-" * 70)
    
    while True:
        try:
            query = input("\\n🔍 Query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\\n👋 Thank you for using the LangGraph Multi-Agent System!")
                break
            
            if not query:
                continue
            
            print("\\n⚡ Processing...")
            result = workflow.process_query(query)
            
            print("\\n📊 Results:")
            print(f"   🎯 Category: {result['classification']['category']}")
            print(f"   📈 Confidence: {result['classification']['confidence']:.2f}")
            print(f"   💭 Reasoning: {result['classification']['reasoning']}")
            print(f"   📚 Sources: {', '.join(result['sources'])}")
            print("\\n💬 Answer:")
            print(f"   {result['answer']}")
            
        except KeyboardInterrupt:
            print("\\n\\n👋 Exiting...")
            break
        except Exception as e:
            print(f"\\n❌ Error: {e}")




if __name__ == "__main__":
    main()