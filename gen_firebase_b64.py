import json, base64, os
from dotenv import load_dotenv

load_dotenv('.env')

pk = os.getenv('FIREBASE_PRIVATE_KEY', '').strip()

# Strip outer quotes if present
if len(pk) >= 2 and pk[0] == pk[-1] and pk[0] in ('"', "'"):
    pk = pk[1:-1]

# Replace escaped newlines with real ones
pk = pk.replace('\\n', '\n')

cred = {
    'type': 'service_account',
    'project_id': os.getenv('FIREBASE_PROJECT_ID', ''),
    'private_key_id': os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
    'private_key': pk,
    'client_email': os.getenv('FIREBASE_CLIENT_EMAIL', ''),
    'client_id': os.getenv('FIREBASE_CLIENT_ID', ''),
    'auth_uri': os.getenv('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
    'token_uri': os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
    'auth_provider_x509_cert_url': os.getenv('FIREBASE_AUTH_PROVIDER_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
    'client_x509_cert_url': os.getenv('FIREBASE_CLIENT_CERT_URL', ''),
}

encoded = base64.b64encode(json.dumps(cred).encode()).decode()

print('=== FIREBASE_CREDENTIALS_BASE64 (copy this entire line) ===')
print(encoded)
print('=== END ===')
print(f'Chars: {len(encoded)}')
print(f'project_id in cred: {cred["project_id"]}')
print(f'private_key starts: {repr(pk[:40])}')
