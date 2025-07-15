import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'html-transform',
      transformIndexHtml(html) {
        // Only inject if we have the environment variables available
        const userPoolId = process.env.VITE_USER_POOL_ID || process.env.USER_POOL_ID;
        const userPoolClientId = process.env.VITE_USER_POOL_CLIENT_ID || process.env.USER_POOL_CLIENT_ID;
        const identityPoolId = process.env.VITE_IDENTITY_POOL_ID || process.env.IDENTITY_POOL_ID;
        const region = process.env.VITE_AWS_REGION || 'us-east-1';
        
        if (!userPoolId || !userPoolClientId || !identityPoolId) {
          console.warn('Missing Cognito credentials in environment variables');
          return html;
        }
        
        // Inject Cognito credentials directly into the HTML
        return html.replace(
          '</head>',
          `<script>
            window.AMPLIFY_AUTH_CONFIG = {
              auth: {
                Cognito: {
                  userPoolId: "${userPoolId}",
                  userPoolClientId: "${userPoolClientId}",
                  identityPoolId: "${identityPoolId}",
                  region: "${region}"
                }
              }
            };
            console.log("Vite plugin injected auth config:", window.AMPLIFY_AUTH_CONFIG);
            
            // Add a global flag for forcing HTTP API connections
            window.FORCE_HTTP_API = ${process.env.VITE_FORCE_HTTP_API === 'true'};
            console.log("HTTP API forced:", window.FORCE_HTTP_API);
          </script>
          </head>`
        );
      }
    }
  ],
  define: {
    // Make environment variables available to the client-side code
    'import.meta.env.VITE_USER_POOL_ID': JSON.stringify(process.env.VITE_USER_POOL_ID || process.env.USER_POOL_ID || ''),
    'import.meta.env.VITE_USER_POOL_CLIENT_ID': JSON.stringify(process.env.VITE_USER_POOL_CLIENT_ID || process.env.USER_POOL_CLIENT_ID || ''),
    'import.meta.env.VITE_IDENTITY_POOL_ID': JSON.stringify(process.env.VITE_IDENTITY_POOL_ID || process.env.IDENTITY_POOL_ID || ''),
    'import.meta.env.VITE_AWS_REGION': JSON.stringify(process.env.VITE_AWS_REGION || 'us-east-1'),
    'import.meta.env.VITE_WINGSIGHT_API_URL': JSON.stringify(process.env.VITE_WINGSIGHT_API_URL || ''),
    'import.meta.env.VITE_API_GATEWAY_URL': JSON.stringify(process.env.VITE_API_GATEWAY_URL || ''),
    'import.meta.env.VITE_FORCE_HTTP_API': JSON.stringify(process.env.VITE_FORCE_HTTP_API === 'true'),
    'import.meta.env.VITE_USE_API_PROXY': JSON.stringify(process.env.VITE_USE_API_PROXY === 'true'),
    'import.meta.env.VITE_API_POLLY':JSON.stringify(process.env.VITE_API_POLLY || '')
  },
  server: {
    proxy: {
      // Proxy API requests when in development mode
      '/v1': {
        target: process.env.VITE_API_GATEWAY_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => {
          const apiUrl = process.env.VITE_API_GATEWAY_URL || '';
          // HTTP API Gateway v2 doesn't use /v1 in the path typically
          // It uses the stage name directly in the URL (like /prod/ or /$default/)
          if (apiUrl.includes('execute-api')) {
            // Remove the /v1 prefix since API Gateway v2 doesn't use it
            return path.replace(/^\/v1/, '');
          }
          
          // Regular backend server (like Django) might use /v1
          return path;
        }
      }
    },
  },
});