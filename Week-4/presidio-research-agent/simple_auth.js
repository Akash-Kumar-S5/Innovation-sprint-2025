
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
                console.log('\nSample documents:');
                data.files.forEach((file, index) => {
                    console.log(`${index + 1}. ${file.name} (ID: ${file.id})`);
                });
            }
        }
        
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
