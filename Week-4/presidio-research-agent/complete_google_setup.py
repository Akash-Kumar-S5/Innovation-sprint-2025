#!/usr/bin/env python3
"""
Complete Google Docs MCP Setup
Handles authentication and testing for the MCP integration
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def setup_google_authentication():
    """Complete the Google authentication setup"""
    
    print("🔑 Setting up Google Docs MCP Authentication...")
    
    # Paths
    project_root = Path(__file__).parent
    creds_dir = project_root / "data" / "google-docs-credentials"
    credentials_path = creds_dir / "credentials.json"
    auth_code_path = creds_dir / "auth_code.txt"
    token_path = creds_dir / "token.json"
    
    # Check if credentials exist
    if not credentials_path.exists():
        print("❌ Google credentials not found!")
        print(f"Expected at: {credentials_path}")
        return False
    
    # Check if auth code exists
    if not auth_code_path.exists():
        print("❌ Authorization code not found!")
        print(f"Expected at: {auth_code_path}")
        print("\nTo get an authorization code:")
        print("1. Visit the OAuth URL from SETUP_INSTRUCTIONS.txt")
        print("2. Complete the authorization flow")
        print("3. Save the code to auth_code.txt")
        return False
    
    print("✅ Found Google credentials and authorization code")
    
    # Create a simple Node.js script for authentication
    auth_script = """
const fs = require('fs');
const path = require('path');

// Simple authentication without googleapis dependency
async function authenticate() {
    try {
        const credentialsPath = path.join(__dirname, 'data', 'google-docs-credentials', 'credentials.json');
        const authCodePath = path.join(__dirname, 'data', 'google-docs-credentials', 'auth_code.txt');
        const tokenPath = path.join(__dirname, 'data', 'google-docs-credentials', 'token.json');
        
        console.log('📝 Reading credentials and auth code...');
        
        const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
        const authCode = fs.readFileSync(authCodePath, 'utf8').trim();
        
        const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
        
        console.log('🔄 Exchanging authorization code for tokens...');
        
        // Use fetch to exchange code for tokens (Node.js 18+ has built-in fetch)
        const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                code: authCode,
                client_id: client_id,
                client_secret: client_secret,
                redirect_uri: redirect_uris[0] || 'urn:ietf:wg:oauth:2.0:oob',
                grant_type: 'authorization_code'
            })
        });
        
        if (!tokenResponse.ok) {
            const error = await tokenResponse.text();
            throw new Error(`Token exchange failed: ${error}`);
        }
        
        const tokens = await tokenResponse.json();
        
        // Save tokens
        fs.writeFileSync(tokenPath, JSON.stringify(tokens, null, 2));
        
        console.log('✅ Authentication successful! Tokens saved.');
        console.log('🎉 Google Docs MCP integration is now ready!');
        
        // Test the tokens by making a simple API call
        const testResponse = await fetch('https://www.googleapis.com/drive/v3/files?q=mimeType%3D%27application%2Fvnd.google-apps.document%27&pageSize=5', {
            headers: {
                'Authorization': `Bearer ${tokens.access_token}`
            }
        });
        
        if (testResponse.ok) {
            const data = await testResponse.json();
            console.log(`📄 Found ${data.files?.length || 0} Google Docs in your Drive`);
            
            if (data.files && data.files.length > 0) {
                console.log('\\nSample documents:');
                data.files.forEach((file, index) => {
                    console.log(`${index + 1}. ${file.name} (ID: ${file.id})`);
                });
            }
        }
        
    } catch (error) {
        console.error('❌ Authentication failed:', error.message);
        
        if (error.message.includes('invalid_grant')) {
            console.log('\\n💡 The authorization code may be expired. Please:');
            console.log('1. Get a new authorization code from the Google OAuth URL');
            console.log('2. Update the auth_code.txt file');
            console.log('3. Run this script again');
        }
        process.exit(1);
    }
}

authenticate();
"""
    
    # Write the authentication script
    auth_script_path = project_root / "simple_auth.js"
    with open(auth_script_path, 'w') as f:
        f.write(auth_script)
    
    print("📝 Created authentication script")
    
    # Run the authentication
    try:
        print("🔄 Running authentication...")
        result = subprocess.run(
            ['node', str(auth_script_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("✅ Authentication completed successfully!")
            
            # Clean up
            auth_script_path.unlink()
            
            # Check if token was created
            if token_path.exists():
                print("✅ Token file created successfully")
                return True
            else:
                print("⚠️ Authentication ran but token file not found")
                return False
        else:
            print(f"❌ Authentication failed with return code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Authentication timed out")
        return False
    except Exception as e:
        print(f"❌ Error running authentication: {e}")
        return False
    finally:
        # Clean up script file
        if auth_script_path.exists():
            auth_script_path.unlink()

def test_mcp_integration():
    """Test the MCP integration"""
    print("\n🧪 Testing MCP Integration...")
    
    try:
        # Import and test the MCP client
        sys.path.append(str(Path(__file__).parent))
        from mcp_client import SimpleMCPClient
        
        client = SimpleMCPClient("mcp-server")
        
        print("📋 Testing Google Docs listing...")
        result = client.list_google_docs()
        
        if result and not result.startswith("Error"):
            print("✅ MCP Google Docs integration working!")
            print("Sample result:", result[:200] + "..." if len(result) > 200 else result)
            return True
        else:
            print("⚠️ MCP integration needs authentication completion")
            print("Result:", result)
            return False
            
    except Exception as e:
        print(f"❌ MCP integration test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Presidio Research Agent - Google Docs MCP Setup")
    print("=" * 60)
    
    # Step 1: Setup authentication
    auth_success = setup_google_authentication()
    
    if not auth_success:
        print("\n❌ Authentication setup failed")
        print("\nManual steps to complete setup:")
        print("1. Ensure you have valid Google OAuth credentials")
        print("2. Get a fresh authorization code from Google")
        print("3. Save the code to data/google-docs-credentials/auth_code.txt")
        print("4. Run this script again")
        return 1
    
    # Step 2: Test MCP integration
    test_success = test_mcp_integration()
    
    if test_success:
        print("\n🎉 Google Docs MCP Integration Setup Complete!")
        print("\nYour Presidio Research Agent now has:")
        print("✅ Real Google Docs search capabilities")
        print("✅ Document content retrieval")
        print("✅ Insurance document access")
        print("✅ Company knowledge base integration")
        
        print("\nNext steps:")
        print("1. Run: python3 agent-core/main.py")
        print("2. Try query: 'Search for insurance policies in Google Docs'")
        print("3. Or run API server: python3 api_server.py")
        
        return 0
    else:
        print("\n⚠️ Setup completed but MCP integration needs verification")
        print("The system will use fallback mode until authentication is fully complete")
        return 0

if __name__ == "__main__":
    exit(main())
