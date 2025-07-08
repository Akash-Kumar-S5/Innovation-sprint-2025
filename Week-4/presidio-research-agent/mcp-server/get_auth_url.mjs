import { google } from 'googleapis';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function getAuthUrl() {
    try {
        const credentialsPath = path.join(__dirname, '..', 'data', 'google-docs-credentials', 'credentials.json');
        
        console.log('🔑 Generating Google OAuth URL...');
        
        const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf8'));
        const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
        
        const auth = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0] || 'http://localhost');
        
        const authUrl = auth.generateAuthUrl({
            access_type: 'offline',
            scope: [
                'https://www.googleapis.com/auth/documents.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ],
            redirect_uri: redirect_uris[0] || 'http://localhost'
        });
        
        console.log('\n📋 GOOGLE OAUTH SETUP INSTRUCTIONS');
        console.log('=' * 50);
        console.log('\n1. Visit this URL in your browser:');
        console.log(authUrl);
        console.log('\n2. Sign in to your Google account');
        console.log('3. Grant permissions to the application');
        console.log('4. You will be redirected to localhost (this will show an error - that\'s normal!)');
        console.log('5. Copy the "code" parameter from the URL in your browser');
        console.log('   Example: http://localhost/?code=YOUR_AUTH_CODE&scope=...');
        console.log('   Copy just the YOUR_AUTH_CODE part');
        console.log('\n6. Save the code to auth_code.txt:');
        console.log('   echo "YOUR_AUTH_CODE" > ../data/google-docs-credentials/auth_code.txt');
        console.log('\n7. Run the authentication script:');
        console.log('   node auth_google.mjs');
        
    } catch (error) {
        console.error('❌ Error generating auth URL:', error.message);
    }
}

getAuthUrl();
