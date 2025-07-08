#!/usr/bin/env node

/**
 * Presidio Google Docs MCP Server
 * Provides Google Docs integration for the Presidio Research Agent
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import { google } from 'googleapis';
import { z } from 'zod';
import * as fs from 'fs/promises';
import * as path from 'path';

// Tool input schemas
const SearchGoogleDocsSchema = z.object({
  query: z.string().describe('Search query for Google Docs'),
});

const ReadGoogleDocSchema = z.object({
  docId: z.string().describe('Google Doc ID to read'),
});

const ListGoogleDocsSchema = z.object({
  maxResults: z.number().optional().default(20).describe('Maximum number of documents to return'),
});

class PresidioGoogleDocsMCPServer {
  private server: Server;
  private auth: any = null;

  constructor() {
    this.server = new Server({
      name: 'presidio-google-docs-mcp-server',
      version: '1.0.0',
      capabilities: {
        tools: {},
      },
    });

    this.setupToolHandlers();
    this.setupErrorHandling();
  }

  private async initializeAuth(): Promise<boolean> {
    try {
      const credentialsPath = path.join(__dirname, '..', '..', 'data', 'google-docs-credentials', 'credentials.json');
      const tokenPath = path.join(__dirname, '..', '..', 'data', 'google-docs-credentials', 'token.json');

      // Load credentials
      const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf8'));
      const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;

      this.auth = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

      // Try to load existing token
      try {
        const token = JSON.parse(await fs.readFile(tokenPath, 'utf8'));
        this.auth.setCredentials(token);
        
        // Test the token
        const drive = google.drive({ version: 'v3', auth: this.auth });
        await drive.files.list({ pageSize: 1 });
        
        return true;
      } catch (error) {
        console.error('Token validation failed:', error);
        return false;
      }
    } catch (error) {
      console.error('Failed to initialize Google auth:', error);
      return false;
    }
  }

  private setupToolHandlers(): void {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'search_google_docs',
            description: 'Search for Google Docs by content or title. Returns matching documents with metadata.',
            inputSchema: {
              type: 'object',
              properties: {
                query: {
                  type: 'string',
                  description: 'Search query for Google Docs content or title',
                },
              },
              required: ['query'],
            },
          },
          {
            name: 'read_google_doc',
            description: 'Read the full content of a specific Google Doc by its ID.',
            inputSchema: {
              type: 'object',
              properties: {
                docId: {
                  type: 'string',
                  description: 'The Google Doc ID to read',
                },
              },
              required: ['docId'],
            },
          },
          {
            name: 'list_google_docs',
            description: 'List all accessible Google Docs with metadata.',
            inputSchema: {
              type: 'object',
              properties: {
                maxResults: {
                  type: 'number',
                  description: 'Maximum number of documents to return (default: 20)',
                  default: 20,
                },
              },
              required: [],
            },
          },
        ] satisfies Tool[],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'search_google_docs':
            return await this.searchGoogleDocs(SearchGoogleDocsSchema.parse(args));
          case 'read_google_doc':
            return await this.readGoogleDoc(ReadGoogleDocSchema.parse(args));
          case 'list_google_docs':
            return await this.listGoogleDocs(ListGoogleDocsSchema.parse(args));
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: 'text',
              text: `Error executing ${name}: ${errorMessage}`,
            },
          ],
        };
      }
    });
  }

  private async searchGoogleDocs(args: z.infer<typeof SearchGoogleDocsSchema>) {
    const authInitialized = await this.initializeAuth();
    
    if (!authInitialized) {
      return {
        content: [
          {
            type: 'text',
            text: `🔍 Google Docs Search Results for: "${args.query}"

⚠️ Authentication Status: Not authenticated

To enable real Google Docs search:
1. Complete the OAuth authentication process
2. Ensure valid tokens are available
3. Verify Google Drive API access

For demonstration, here are sample insurance-related documents that would be found:

📄 **Sample Insurance Documents:**

1. **Presidio Insurance Claims Processing Guide**
   - Document ID: 1ABC123_sample_claims_guide
   - Last Modified: 2024-01-15
   - Content Preview: "This document outlines the standard procedures for processing insurance claims at Presidio. Key steps include initial assessment, documentation review, fraud detection protocols..."

2. **Customer Insurance Policy Templates**
   - Document ID: 2DEF456_policy_templates  
   - Last Modified: 2024-01-10
   - Content Preview: "Standard policy templates for different insurance products including auto, home, life, and commercial coverage options..."

3. **Insurance Regulatory Compliance Manual**
   - Document ID: 3GHI789_compliance_manual
   - Last Modified: 2024-01-08
   - Content Preview: "Comprehensive guide to insurance regulatory requirements, state-specific compliance rules, and reporting obligations..."

💡 **Note**: These are sample results. With proper authentication, the system would search your actual Google Drive for documents containing "${args.query}".`,
          },
        ],
      };
    }

    try {
      const drive = google.drive({ version: 'v3', auth: this.auth });
      
      // Search for Google Docs containing the query
      const response = await drive.files.list({
        q: `mimeType='application/vnd.google-apps.document' and fullText contains '${args.query}'`,
        fields: 'files(id, name, createdTime, modifiedTime, webViewLink, owners)',
        pageSize: 10,
      });

      const files = response.data.files || [];

      if (files.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: `🔍 Google Docs Search Results for: "${args.query}"

No documents found matching your search query.

Try:
- Using different keywords
- Checking spelling
- Using broader search terms
- Ensuring you have access to the documents`,
            },
          ],
        };
      }

      let resultText = `🔍 Google Docs Search Results for: "${args.query}"\n\nFound ${files.length} matching documents:\n\n`;

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        resultText += `${i + 1}. **${file.name}**\n`;
        resultText += `   📄 Document ID: ${file.id}\n`;
        resultText += `   📅 Modified: ${file.modifiedTime}\n`;
        resultText += `   🔗 Link: ${file.webViewLink}\n`;
        if (file.owners && file.owners.length > 0) {
          resultText += `   👤 Owner: ${file.owners[0].displayName || file.owners[0].emailAddress}\n`;
        }
        resultText += '\n';
      }

      return {
        content: [
          {
            type: 'text',
            text: resultText,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Error searching Google Docs: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
      };
    }
  }

  private async readGoogleDoc(args: z.infer<typeof ReadGoogleDocSchema>) {
    const authInitialized = await this.initializeAuth();
    
    if (!authInitialized) {
      return {
        content: [
          {
            type: 'text',
            text: `📄 Reading Google Doc: ${args.docId}

⚠️ Authentication Status: Not authenticated

Sample document content for demonstration:

**PRESIDIO INSURANCE POLICY DOCUMENT**

Policy Number: POL-2024-${args.docId.slice(-6)}
Effective Date: January 1, 2024
Policy Holder: [Sample Customer]

**Coverage Details:**
- Auto Insurance: $500,000 liability
- Comprehensive Coverage: $50,000
- Collision Coverage: $50,000
- Deductible: $500

**Claims Process:**
1. Report incident within 24 hours
2. Provide documentation and photos
3. Schedule vehicle inspection
4. Receive claim decision within 5 business days

**Contact Information:**
- Claims Hotline: 1-800-PRESIDIO
- Online Portal: claims.presidio.com
- Emergency Assistance: Available 24/7

💡 **Note**: This is sample content. With proper authentication, the system would read the actual Google Doc content.`,
          },
        ],
      };
    }

    try {
      const docs = google.docs({ version: 'v1', auth: this.auth });
      
      // Get document content
      const response = await docs.documents.get({
        documentId: args.docId,
      });

      const doc = response.data;
      let content = `📄 **${doc.title}**\n\n`;

      if (doc.body && doc.body.content) {
        for (const element of doc.body.content) {
          if (element.paragraph) {
            for (const textElement of element.paragraph.elements || []) {
              if (textElement.textRun) {
                content += textElement.textRun.content || '';
              }
            }
          }
        }
      }

      return {
        content: [
          {
            type: 'text',
            text: content,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Error reading Google Doc: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
      };
    }
  }

  private async listGoogleDocs(args: z.infer<typeof ListGoogleDocsSchema>) {
    const authInitialized = await this.initializeAuth();
    
    if (!authInitialized) {
      return {
        content: [
          {
            type: 'text',
            text: `📋 **Available Google Docs**

⚠️ Authentication Status: Not authenticated

Sample insurance-related documents for demonstration:

**📄 PRESIDIO INSURANCE DOCUMENTS:**

1. **Auto Insurance Policy Template**
   - Document ID: 1a2b3c4d5e6f_auto_policy
   - Created: 2024-01-15
   - Modified: 2024-01-20
   - Owner: insurance.team@presidio.com

2. **Home Insurance Claims Guide**
   - Document ID: 2b3c4d5e6f7g_home_claims
   - Created: 2024-01-12
   - Modified: 2024-01-18
   - Owner: claims.dept@presidio.com

3. **Life Insurance Underwriting Manual**
   - Document ID: 3c4d5e6f7g8h_life_underwriting
   - Created: 2024-01-10
   - Modified: 2024-01-16
   - Owner: underwriting@presidio.com

4. **Commercial Insurance Risk Assessment**
   - Document ID: 4d5e6f7g8h9i_commercial_risk
   - Created: 2024-01-08
   - Modified: 2024-01-14
   - Owner: commercial.team@presidio.com

5. **Insurance Fraud Detection Procedures**
   - Document ID: 5e6f7g8h9i0j_fraud_detection
   - Created: 2024-01-05
   - Modified: 2024-01-12
   - Owner: fraud.prevention@presidio.com

💡 **Note**: These are sample documents. With proper authentication, the system would list your actual Google Docs from Google Drive.`,
          },
        ],
      };
    }

    try {
      const drive = google.drive({ version: 'v3', auth: this.auth });
      
      const response = await drive.files.list({
        q: "mimeType='application/vnd.google-apps.document'",
        fields: 'files(id, name, createdTime, modifiedTime, webViewLink, owners)',
        pageSize: args.maxResults,
        orderBy: 'modifiedTime desc',
      });

      const files = response.data.files || [];

      if (files.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: '📋 No Google Docs found in your Drive.',
            },
          ],
        };
      }

      let resultText = `📋 **Available Google Docs** (${files.length} documents)\n\n`;

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        resultText += `${i + 1}. **${file.name}**\n`;
        resultText += `   📄 Document ID: ${file.id}\n`;
        resultText += `   📅 Created: ${file.createdTime}\n`;
        resultText += `   📅 Modified: ${file.modifiedTime}\n`;
        resultText += `   🔗 Link: ${file.webViewLink}\n`;
        if (file.owners && file.owners.length > 0) {
          resultText += `   👤 Owner: ${file.owners[0].displayName || file.owners[0].emailAddress}\n`;
        }
        resultText += '\n';
      }

      return {
        content: [
          {
            type: 'text',
            text: resultText,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Error listing Google Docs: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
      };
    }
  }

  private setupErrorHandling(): void {
    this.server.onerror = (error) => {
      console.error('[MCP Error]', error);
    };

    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Presidio Google Docs MCP Server running on stdio');
  }
}

// Start the server
const server = new PresidioGoogleDocsMCPServer();
server.run().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});
