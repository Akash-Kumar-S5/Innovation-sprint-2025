"""
MCP Client for Google Docs Integration
Communicates with the TypeScript MCP server
"""

import subprocess
import json
import logging
import os
from typing import Dict, Any, List, Optional
import asyncio
import tempfile

logger = logging.getLogger(__name__)

class GoogleDocsMCPClient:
    """
    Client to communicate with the Google Docs MCP server
    """
    
    def __init__(self, server_path: str = "mcp-server"):
        self.server_path = server_path
        self.server_process = None
        self.is_connected = False
        
    async def start_server(self):
        """Start the MCP server process"""
        try:
            server_script = os.path.join(self.server_path, "src", "server.ts")
            if not os.path.exists(server_script):
                logger.error(f"MCP server script not found at {server_script}")
                return False
            
            # Start the server process
            self.server_process = await asyncio.create_subprocess_exec(
                "node", server_script,
                cwd=self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.is_connected = True
            logger.info("✅ MCP server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False
    
    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server"""
        if not self.is_connected or not self.server_process:
            raise Exception("MCP server not connected")
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_json.encode())
            await self.server_process.stdin.drain()
            
            # Read response
            response_line = await self.server_process.stdout.readline()
            response = json.loads(response_line.decode().strip())
            
            if "error" in response:
                raise Exception(f"MCP server error: {response['error']}")
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            raise
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server"""
        try:
            result = await self.send_request("tools/list", {})
            return result.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}")
            return []
    
    async def search_google_docs(self, query: str) -> str:
        """Search Google Docs using the MCP server"""
        try:
            result = await self.send_request("tools/call", {
                "name": "search_google_docs",
                "arguments": {"query": query}
            })
            
            content = result.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "No results found")
            
            return "No results found"
            
        except Exception as e:
            logger.error(f"Google Docs search failed: {e}")
            return f"Error searching Google Docs: {str(e)}"
    
    async def read_google_doc(self, doc_id: str) -> str:
        """Read a specific Google Doc by ID"""
        try:
            result = await self.send_request("tools/call", {
                "name": "read_google_doc",
                "arguments": {"docId": doc_id}
            })
            
            content = result.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "No content found")
            
            return "No content found"
            
        except Exception as e:
            logger.error(f"Failed to read Google Doc: {e}")
            return f"Error reading Google Doc: {str(e)}"
    
    async def list_google_docs(self) -> str:
        """List all accessible Google Docs"""
        try:
            result = await self.send_request("tools/call", {
                "name": "list_google_docs",
                "arguments": {}
            })
            
            content = result.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "No documents found")
            
            return "No documents found"
            
        except Exception as e:
            logger.error(f"Failed to list Google Docs: {e}")
            return f"Error listing Google Docs: {str(e)}"
    
    async def stop_server(self):
        """Stop the MCP server process"""
        if self.server_process:
            self.server_process.terminate()
            await self.server_process.wait()
            self.is_connected = False
            logger.info("MCP server stopped")

class SimpleMCPClient:
    """
    Simplified synchronous MCP client for easier integration
    """
    
    def __init__(self, server_path: str = "mcp-server"):
        self.server_path = server_path
        self.server_dir = os.path.abspath(server_path)
        
    def _run_mcp_command(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Run an MCP command using subprocess"""
        try:
            # Create a temporary script to run the MCP command
            script_content = f"""
const {{ google }} = require('googleapis');
const fs = require('fs').promises;
const path = require('path');

async function runTool() {{
    try {{
        const credentialsPath = path.join(__dirname, '..', 'data', 'google-docs-credentials', 'credentials.json');
        const tokenPath = path.join(__dirname, '..', 'data', 'google-docs-credentials', 'token.json');
        
        // Load credentials
        const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf8'));
        const {{ client_secret, client_id, redirect_uris }} = credentials.installed || credentials.web;
        
        const auth = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);
        
        // Try to load existing token
        try {{
            const token = JSON.parse(await fs.readFile(tokenPath, 'utf8'));
            auth.setCredentials(token);
        }} catch (error) {{
            console.log('No valid token found. Please run authentication first.');
            return;
        }}
        
        // Execute the tool
        if ('{tool_name}' === 'search_google_docs') {{
            const drive = google.drive({{ version: 'v3', auth }});
            const response = await drive.files.list({{
                q: `mimeType='application/vnd.google-apps.document' and fullText contains '{arguments.get('query', '')}'`,
                fields: 'files(id, name, createdTime, modifiedTime, webViewLink)',
                pageSize: 10
            }});
            
            const results = response.data.files || [];
            if (results.length === 0) {{
                console.log('No documents found matching the query.');
            }} else {{
                console.log(`Found ${{results.length}} documents:`);
                results.forEach((doc, index) => {{
                    console.log(`${{index + 1}}. ${{doc.name}}`);
                    console.log(`   ID: ${{doc.id}}`);
                    console.log(`   Modified: ${{doc.modifiedTime}}`);
                    console.log(`   Link: ${{doc.webViewLink}}`);
                    console.log('');
                }});
            }}
        }} else if ('{tool_name}' === 'list_google_docs') {{
            const drive = google.drive({{ version: 'v3', auth }});
            const response = await drive.files.list({{
                q: "mimeType='application/vnd.google-apps.document'",
                fields: 'files(id, name, createdTime, modifiedTime, webViewLink)',
                pageSize: 20,
                orderBy: 'modifiedTime desc'
            }});
            
            const docs = response.data.files || [];
            if (docs.length === 0) {{
                console.log('No Google Docs found in your Drive');
            }} else {{
                console.log(`Found ${{docs.length}} Google Docs:`);
                docs.forEach((doc, index) => {{
                    console.log(`${{index + 1}}. ${{doc.name}}`);
                    console.log(`   ID: ${{doc.id}}`);
                    console.log(`   Modified: ${{doc.modifiedTime}}`);
                    console.log(`   Link: ${{doc.webViewLink}}`);
                    console.log('');
                }});
            }}
        }}
        
    }} catch (error) {{
        console.error('Error:', error.message);
    }}
}}

runTool();
"""
            
            # Write the script to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(script_content)
                temp_script = f.name
            
            try:
                # Run the script
                result = subprocess.run(
                    ['node', temp_script],
                    cwd=self.server_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    return f"Error: {result.stderr.strip()}"
                    
            finally:
                # Clean up the temporary file
                try:
                    os.unlink(temp_script)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"MCP command failed: {e}")
            return f"Error executing MCP command: {str(e)}"
    
    def search_google_docs(self, query: str) -> str:
        """Search Google Docs"""
        return self._run_mcp_command("search_google_docs", {"query": query})
    
    def list_google_docs(self) -> str:
        """List Google Docs"""
        return self._run_mcp_command("list_google_docs", {})
    
    def read_google_doc(self, doc_id: str) -> str:
        """Read a specific Google Doc"""
        return self._run_mcp_command("read_google_doc", {"docId": doc_id})
