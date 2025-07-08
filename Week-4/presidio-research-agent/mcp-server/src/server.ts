import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  CallToolRequest,
  ListToolsRequest,
  McpError,
  ErrorCode,
} from "@modelcontextprotocol/sdk/types.js";
import { google } from 'googleapis';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

// Redirect console.log to stderr to avoid breaking MCP protocol
const originalLog = console.log;
console.log = (...args) => {
  console.error('[MCP Server]', ...args);
};

class GoogleDocsMCPServer {
  private server: Server;
  private auth: any;
  private isAuthenticated: boolean = false;

  constructor() {
    this.server = new Server(
      {
        name: "presidio-google-docs-mcp",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
  }

  private getCredentialsPath(): string {
    // Get the directory of the current script
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    
    // Go up to project root and find credentials
    const projectRoot = path.resolve(__dirname, '../../');
    return path.join(projectRoot, 'data/google-docs-credentials/credentials.json');
  }

  private getTokenPath(): string {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const projectRoot = path.resolve(__dirname, '../../');
    return path.join(projectRoot, 'data/google-docs-credentials/token.json');
  }

  private async ensureDirectoryExists(filePath: string): Promise<void> {
    const dir = path.dirname(filePath);
    try {
      await fs.mkdir(dir, { recursive: true });
    } catch (error) {
      // Directory might already exist, ignore error
    }
  }

  private async setupGoogleAuth(): Promise<void> {
    const credentialsPath = this.getCredentialsPath();
    const tokenPath = this.getTokenPath();

    console.error(`[Auth] Looking for credentials at: ${credentialsPath}`);
    console.error(`[Auth] Looking for token at: ${tokenPath}`);

    // Ensure directories exist
    await this.ensureDirectoryExists(credentialsPath);
    await this.ensureDirectoryExists(tokenPath);

    // Check if credentials exist
    try {
      await fs.access(credentialsPath);
    } catch (error) {
      const sampleCredentials = {
        "installed": {
          "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
          "project_id": "your-project-id",
          "auth_uri": "https://accounts.google.com/o/oauth2/auth",
          "token_uri": "https://oauth2.googleapis.com/token",
          "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
          "client_secret": "YOUR_CLIENT_SECRET",
          "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost/8000"]
        }
      };

      await fs.writeFile(credentialsPath, JSON.stringify(sampleCredentials, null, 2));
      
      throw new Error(`
🔑 SETUP REQUIRED: Google credentials not found.

I've created a template file at: ${credentialsPath}

Please:
1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create a project and enable Google Docs & Drive APIs
3. Create OAuth 2.0 credentials (Desktop application)
4. Download the credentials.json file
5. Replace the template file with your actual credentials.json
6. Restart the MCP server

The template has been created for you to replace.
      `);
    }

    // Load credentials
    const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf8'));
    const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;

    if (!client_secret || !client_id || client_secret.includes('YOUR_CLIENT') || client_id.includes('YOUR_CLIENT')) {
      throw new Error(`
🔑 SETUP REQUIRED: Please update your credentials.json file.

The file at ${credentialsPath} contains placeholder values.
Please replace it with your actual Google OAuth credentials.

To get credentials:
1. Go to Google Cloud Console
2. Enable Google Docs & Drive APIs
3. Create OAuth 2.0 credentials (Desktop application)
4. Download and replace the credentials.json file
      `);
    }

    this.auth = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

    // Check for existing token
    try {
      const token = JSON.parse(await fs.readFile(tokenPath, 'utf8'));
      
      if (!token.access_token) {
        throw new Error('Invalid token format');
      }

      this.auth.setCredentials(token);
      
      // Test the token
      const drive = google.drive({ version: 'v3', auth: this.auth });
      await drive.files.list({ pageSize: 1 });
      
      console.error('[Auth] ✅ Existing token is valid');
      this.isAuthenticated = true;
      return;

    } catch (error) {
      console.error('[Auth] Token invalid or missing, starting OAuth flow...');
      await this.performOAuthFlow(tokenPath);
    }
  }

  private async performOAuthFlow(tokenPath: string): Promise<void> {
    // Use out-of-band flow to avoid localhost issues
    const authUrl = this.auth.generateAuthUrl({
      access_type: 'offline',
      scope: [
        'https://www.googleapis.com/auth/documents.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
      ],
      redirect_uri: 'urn:ietf:wg:oauth:2.0:oob'  // This avoids localhost
    });

    // Create a simple instruction file for the user
    const instructionPath = path.join(path.dirname(tokenPath), 'SETUP_INSTRUCTIONS.txt');
    const instructions = `
🔑 GOOGLE AUTHENTICATION REQUIRED

Your MCP server needs Google authentication to access Google Docs.

STEP 1: Authorize the application
Visit this URL in your browser:
${authUrl}

STEP 2: Get the authorization code
- Sign in to your Google account
- Grant permissions to the application  
- You'll see a page with "Please copy this code, switch to your application and paste it there:"
- Copy the authorization code (it will be a long string)

STEP 3: Set the authorization code
Choose ONE of these methods:

Method A - Environment variable:
export GOOGLE_AUTH_CODE="paste_your_code_here"

Method B - Create auth_code.txt file:
echo "paste_your_code_here" > auth_code.txt

STEP 4: Restart the MCP server
The server will automatically exchange the code for tokens.

IMPORTANT: Don't worry about the "localhost refused to connect" error - that's normal!
Just copy the code from the Google page.

This file was created: ${new Date().toISOString()}
`;

    await fs.writeFile(instructionPath, instructions);

    // Check for auth code in environment variable
    const authCode = process.env.GOOGLE_AUTH_CODE;
    if (authCode) {
      await this.exchangeCodeForTokens(authCode.trim(), tokenPath);
      return;
    }

    // Check for auth code in file
    const authCodePath = path.join(path.dirname(tokenPath), 'auth_code.txt');
    try {
      const fileAuthCode = (await fs.readFile(authCodePath, 'utf8')).trim();
      if (fileAuthCode) {
        await this.exchangeCodeForTokens(fileAuthCode, tokenPath);
        // Clean up the auth code file
        await fs.unlink(authCodePath);
        return;
      }
    } catch (error) {
      // File doesn't exist, that's fine
    }

    throw new Error(`
🔑 GOOGLE AUTHENTICATION REQUIRED

Please complete the authentication setup:

1. Open this file for detailed instructions:
   ${instructionPath}

2. Visit the authorization URL (IGNORE the localhost error - that's normal!)

3. Copy the authorization code from Google's page

4. Either:
   - Set GOOGLE_AUTH_CODE environment variable, OR
   - Create auth_code.txt file with your code

5. Restart the MCP server

The authorization URL is:
${authUrl}

NOTE: You can ignore any "localhost refused to connect" errors - just copy the code!
    `);
  }

  private async exchangeCodeForTokens(code: string, tokenPath: string): Promise<void> {
    try {
      console.error('[Auth] Exchanging authorization code for tokens...');
      const { tokens } = await this.auth.getToken(code);
      
      this.auth.setCredentials(tokens);
      
      // Save tokens
      await fs.writeFile(tokenPath, JSON.stringify(tokens, null, 2));
      
      // Test the authentication
      const drive = google.drive({ version: 'v3', auth: this.auth });
      const testResponse = await drive.files.list({ pageSize: 1 });
      
      console.error('[Auth] ✅ Authentication successful!');
      console.error(`[Auth] Found ${testResponse.data.files?.length || 0} Google Docs in your Drive`);
      
      this.isAuthenticated = true;

    } catch (error) {
      let errorMessage = 'Failed to exchange authorization code for tokens.';

      if (typeof error === 'object' && error !== null && 'message' in error && typeof (error as any).message === 'string') {
        if ((error as any).message.includes('invalid_grant')) {
          errorMessage += ' The authorization code is invalid, expired, or already used. Please get a new code.';
        } else if ((error as any).message.includes('invalid_client')) {
          errorMessage += ' Invalid client credentials. Please check your credentials.json file.';
        }
        throw new Error(errorMessage + ` Error: ${(error as any).message}`);
      } else {
        throw new Error(errorMessage + ` Error: ${String(error)}`);
      }
    }
  }

  private async initializeAuth(): Promise<void> {
    if (this.isAuthenticated) {
      return; // Already authenticated
    }

    try {
      await this.setupGoogleAuth();
    } catch (error) {
      if (error instanceof Error) {
        console.error('[Auth] Authentication failed:', error.message);
      } else {
        console.error('[Auth] Authentication failed:', String(error));
      }
      throw error;
    }
  }

  private setupToolHandlers() {
    // Handle tool listing
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "read_google_doc",
            description: "Read content from a specific Google Doc by ID",
            inputSchema: {
              type: "object",
              properties: {
                docId: {
                  type: "string",
                  description: "The Google Doc ID to read"
                }
              },
              required: ["docId"]
            }
          },
          {
            name: "search_google_docs",
            description: "Search for Google Docs containing specific terms",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Search query for finding relevant documents"
                }
              },
              required: ["query"]
            }
          },
          {
            name: "list_google_docs",
            description: "List all accessible Google Docs",
            inputSchema: {
              type: "object",
              properties: {}
            }
          }
        ]
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest) => {
      const { name, arguments: args } = request.params;

      try {
        await this.initializeAuth();

        switch (name) {
          case "read_google_doc":
            if (!args?.docId) {
              throw new Error("Document ID is required");
            }
            return await this.readGoogleDoc(args.docId as string);
          
          case "search_google_docs":
            if (!args?.query) {
              throw new Error("Search query is required");
            }
            return await this.searchGoogleDocs(args.query as string);
          
          case "list_google_docs":
            return await this.listGoogleDocs();
          
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`
            );
        }
      } catch (error) {
        const errorMessage = (error instanceof Error) ? error.message : String(error);
        console.error(`Error executing tool ${name}:`, errorMessage);
        throw new McpError(
          ErrorCode.InternalError,
          `Error executing tool ${name}: ${errorMessage}`
        );
      }
    });
  }

  private async readGoogleDoc(docId: string) {
    try {
      const docs = google.docs({ version: 'v1', auth: this.auth });
      const response = await docs.documents.get({ documentId: docId });
      
      const content = this.extractTextFromDoc(response.data);
      const title = response.data.title || 'Untitled Document';
      
      return {
        content: [{
          type: "text",
          text: `Document: ${title}\n\nContent:\n${content}`
        }]
      };
    } catch (error) {
      let errorMessage: string;
      if (typeof error === 'object' && error !== null && 'code' in error && (error as any).code === 404) {
        errorMessage = `Document not found or no access: ${docId}`;
      } else if (typeof error === 'object' && error !== null && 'message' in error) {
        errorMessage = `Error reading document: ${(error as any).message}`;
      } else {
        errorMessage = 'An unknown error occurred while reading the document.';
      }
      
      return {
        content: [{
          type: "text", 
          text: errorMessage
        }]
      };
    }
  }

  private async searchGoogleDocs(query: string) {
    try {
      const drive = google.drive({ version: 'v3', auth: this.auth });
      const response = await drive.files.list({
        q: `mimeType='application/vnd.google-apps.document' and fullText contains '${query}'`,
        fields: 'files(id, name, createdTime, modifiedTime, webViewLink)',
        pageSize: 20
      });

      const results = response.data.files?.map(file => ({
        id: file.id,
        name: file.name,
        created: file.createdTime,
        modified: file.modifiedTime,
        link: file.webViewLink
      })) || [];

      if (results.length === 0) {
        return {
          content: [{
            type: "text",
            text: `No documents found matching "${query}"`
          }]
        };
      }

      const resultText = results.map((doc, index) => 
        `${index + 1}. ${doc.name}\n   ID: ${doc.id}\n   Modified: ${doc.modified}\n   Link: ${doc.link}\n`
      ).join('\n');

      return {
        content: [{
          type: "text",
          text: `Found ${results.length} documents matching "${query}":\n\n${resultText}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error searching documents: ${error instanceof Error ? error.message : String(error)}`
        }]
      };
    }
  }

  private async listGoogleDocs() {
    try {
      const drive = google.drive({ version: 'v3', auth: this.auth });
      const response = await drive.files.list({
        q: "mimeType='application/vnd.google-apps.document'",
        fields: 'files(id, name, createdTime, modifiedTime, webViewLink)',
        pageSize: 50,
        orderBy: 'modifiedTime desc'
      });

      const docs = response.data.files?.map(file => ({
        id: file.id,
        name: file.name,
        created: file.createdTime,
        modified: file.modifiedTime,
        link: file.webViewLink
      })) || [];

      if (docs.length === 0) {
        return {
          content: [{
            type: "text",
            text: "No Google Docs found in your Drive"
          }]
        };
      }

      const docList = docs.map((doc, index) => 
        `${index + 1}. ${doc.name}\n   ID: ${doc.id}\n   Modified: ${doc.modified}\n   Link: ${doc.link}\n`
      ).join('\n');

      return {
        content: [{
          type: "text",
          text: `Found ${docs.length} Google Docs:\n\n${docList}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error listing documents: ${error instanceof Error ? error.message : String(error)}`
        }]
      };
    }
  }

  private extractTextFromDoc(doc: any): string {
    if (!doc.body?.content) return 'No content found';
    
    let text = '';
    
    const processContent = (elements: any[]) => {
      for (const element of elements) {
        if (element.paragraph) {
          for (const textElement of element.paragraph.elements || []) {
            if (textElement.textRun?.content) {
              text += textElement.textRun.content;
            }
          }
          text += '\n';
        } else if (element.table) {
          // Handle tables
          text += '\n[TABLE]\n';
          for (const row of element.table.tableRows || []) {
            const cellTexts = [];
            for (const cell of row.tableCells || []) {
              let cellText = '';
              for (const cellElement of cell.content || []) {
                if (cellElement.paragraph) {
                  for (const textElement of cellElement.paragraph.elements || []) {
                    if (textElement.textRun?.content) {
                      cellText += textElement.textRun.content.trim();
                    }
                  }
                }
              }
              cellTexts.push(cellText || '');
            }
            text += cellTexts.join(' | ') + '\n';
          }
          text += '[/TABLE]\n\n';
        }
      }
    };

    processContent(doc.body.content);
    return text.trim();
  }

  async start() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Google Docs MCP Server started successfully");
  }
}

// Start the server
const server = new GoogleDocsMCPServer();
server.start().catch((error) => {
  console.error("Failed to start server:", error);
  process.exit(1);
});