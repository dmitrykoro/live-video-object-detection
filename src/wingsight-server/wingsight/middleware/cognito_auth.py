import os

import jwt
import time
import requests

from jwt import PyJWKClient

from django.http import JsonResponse
from dotenv import load_dotenv

load_dotenv()

COGNITO_REGION = os.getenv('AWS_REGION')
USER_POOL_ID = os.getenv('USER_POOL_ID')
APP_CLIENT_ID = os.getenv('APP_CLIENT_ID')
COGNITO_ISSUER = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}'
JWKS_URL = f'{COGNITO_ISSUER}/.well-known/jwks.json'

# Internal JWKS cache to avoid re-downloading on every request
_jwks_cache = {
    'keys': None,
    'timestamp': 0,
    'ttl': 3600  # Refresh every hour
}

jwk_client = PyJWKClient(JWKS_URL)

def get_jwks():
    now = time.time()

    if _jwks_cache['keys'] is None or now - _jwks_cache['timestamp'] > _jwks_cache['ttl']:
        try:
            response = requests.get(JWKS_URL)
            response.raise_for_status()
            _jwks_cache['keys'] = response.json()['keys']
            _jwks_cache['timestamp'] = now

        except requests.RequestException:
            _jwks_cache['keys'] = None

    return _jwks_cache['keys']


def get_public_key(token):
    return jwk_client.get_signing_key_from_jwt(token).key


class CognitoAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth = request.headers.get('Authorization', None)

        if not auth or not auth.startswith('Bearer '):
            return JsonResponse({'error': 'Unauthorized: Missing token'}, status=401)

        token = auth.split(' ')[1]
        try:
            key = get_public_key(token)
            if not key:
                raise ValueError("Public key not found")

            payload = jwt.decode(
                token,
                key=key,
                audience=APP_CLIENT_ID,
                issuer=COGNITO_ISSUER,
                algorithms=['RS256'],
                options={"verify_signature": True},
            )
            request.user_payload = payload

        except Exception as e:
            return JsonResponse({'error': f'Unauthorized: {str(e)}'}, status=401)

        return self.get_response(request)
