function getEnvVariable(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing environment variable: ${key}`);
  }
  return value;
}

import { referenceAuth } from '@aws-amplify/backend';

// Add fallback for region in case AWS_REGION is not available
function getRegion(): string {
  return process.env.REGION || process.env.VITE_AWS_REGION || 'us-east-1';
}

export const auth = referenceAuth({
  userPoolId: getEnvVariable("USER_POOL_ID"),
  identityPoolId: getEnvVariable("IDENTITY_POOL_ID"),
  authRoleArn: getEnvVariable("AUTH_ROLE_ARN"),
  unauthRoleArn: getEnvVariable("UNAUTH_ROLE_ARN"),
  userPoolClientId: getEnvVariable("USER_POOL_CLIENT_ID"),
  region: getRegion()  // Use our helper function for region instead of direct environment variable
});
