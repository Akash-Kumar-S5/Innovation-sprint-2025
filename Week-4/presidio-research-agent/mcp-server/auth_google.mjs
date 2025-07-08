import { google } from 'googleapis';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function authenticate() {
    try {
        const credentialsPath = path.join(__dirname, '..', 'data', 'google-docs-credentials', 'credentials.json');
        const authCodePath = path.join(__dirname, '..', 'data', 'google-docs-credentials', 'auth_code.txt');
        const tokenPath = path.join(__dirname, '..', 'data', 'google-docs-credentials', 'token.json');
        
        console.log('🔑 Setting up Google authentication...');
        console.log('📝 Reading credentials and auth code...');
        
        const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf8'));
        const authCode = (await fs.readFile(authCodePath, 'utf8')).trim();
        
        const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
        
        const auth = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0] || 'http://localhost');
        
        console.log('🔄 Exchanging authorization code for tokens...');
        
        // Exchange code for tokens
        const { tokens } = await auth.getToken(authCode);
        auth.setCredentials(tokens);
        
        // Save tokens
        await fs.writeFile(tokenPath, JSON.stringify(tokens, null, 2));
        console.log('💾 Tokens saved successfully');
        
        // Test the authentication
        const drive = google.drive({ version: 'v3', auth });
        const response = await drive.files.list({ 
            q: "mimeType='application/vnd.google-apps.document'",
            pageSize: 5 
        });
        
        console.log(`✅ Authentication successful! Found ${response.data.files?.length || 0} Google Docs`);
        
        if (response.data.files && response.data.files.length > 0) {
            console.log('\n📄 Sample documents:');
            response.data.files.forEach((file, index) => {
                console.log(`${index + 1}. ${file.name} (ID: ${file.id})`);
            });
        }
        
        console.log('\n🎉 Google Docs MCP integration is now ready!');
        
    } catch (error) {
        console.error('❌ Authentication failed:', error.message);
        
        if (error.message.includes('invalid_grant')) {
            console.log('\n💡 The authorization code may be expired. Please:');
            console.log('1. Get a new authorization code from the Google OAuth URL');
            console.log('2. Update the auth_code.txt file');
            console.log('3. Run this script again');
        }
        process.exit(1);
    }
}

authenticate();
