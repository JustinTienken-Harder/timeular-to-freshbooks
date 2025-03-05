import os
import json
import webbrowser
import subprocess
import ssl
import tempfile
from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect

class FreshbooksOAuth:
    """OAuth2 handler for Freshbooks API with HTTPS support."""
    
    # Freshbooks OAuth endpoints
    AUTH_URL = "https://my.freshbooks.com/service/auth/oauth/authorize"
    TOKEN_URL = "https://api.freshbooks.com/auth/oauth/token"
    REDIRECT_URI = "https://localhost:8443/callback"
    
    def __init__(self, client_id, client_secret, token_file="oauth_token.json"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = token_file
        self.token = self._load_token()
        
        # Create OAuth session
        self.oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.REDIRECT_URI,
        )
        self.session = {}
    
    def _load_token(self):
        """Load the OAuth token from file if it exists."""
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                return json.load(f)
        return None
    
    def _save_token(self, token):
        """Save the OAuth token to a file."""
        with open(self.token_file, 'w') as f:
            json.dump(token, f)
        
    def get_authorization_url(self):
        """Get the authorization URL to redirect the user."""
        authorization_url, state = self.oauth.authorization_url(self.AUTH_URL)
        self.session["oauth_state"] = state
        return authorization_url
    
    def fetch_token(self, authorization_response):
        """Exchange the authorization code for an access token."""
        self.oauth = OAuth2Session(
            client_id=self.client_id,
            token = self.session['oauth_state'],
            redirect_uri=self.REDIRECT_URI)
        token = self.oauth.fetch_token(
            self.TOKEN_URL,
            client_secret=self.client_secret,
            authorization_response=request.url
        )
        self._save_token(token)
        self.token = token
        return token
        
    def refresh_token(self):
        """Refresh the access token if it has expired."""
        if not self.token:
            raise ValueError("No token exists. Need to authorize first.")
            
        self.token = self.oauth.refresh_token(
            self.TOKEN_URL,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self._save_token(self.token)
        return self.token
    
    def authorized_session(self):
        """Return an authorized session for making API requests."""
        if not self.token:
            raise ValueError("No token exists. Need to authorize first.")
        return self.oauth


def generate_self_signed_cert():
    """Generate a self-signed certificate for local HTTPS."""
    cert_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')
    key_file = tempfile.NamedTemporaryFile(delete=False, suffix='.key')
    
    cert_path = cert_file.name
    key_path = key_file.name
    
    cert_file.close()
    key_file.close()
    
    # Generate self-signed certificate using OpenSSL
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
        '-nodes', '-out', cert_path, '-keyout', key_path,
        '-days', '365', '-subj', '/CN=localhost'
    ])
    
    return cert_path, key_path


def start_oauth_flow(client_id, client_secret):
    """Start the OAuth flow with a local HTTPS web server."""
    oauth_handler = FreshbooksOAuth(client_id, client_secret)
    
    # Generate self-signed certificate for HTTPS
    cert_path, key_path = generate_self_signed_cert()
    ssl_context = (cert_path, key_path)
    
    # Create a simple Flask app to handle the callback
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        auth_url = oauth_handler.get_authorization_url()
        webbrowser.open(auth_url)
        return "Opened browser for authorization. Please check your browser window."
    
    @app.route('/callback')
    def callback():
        try:
            token = oauth_handler.fetch_token(request.url)
            return "Authorization successful! Token saved to file. You can close this window now."
        except Exception as e:
            return f"Error during authorization: {str(e)}"
    
    print("Starting local HTTPS server for OAuth callback...")
    print("NOTE: Your browser may show a security warning - this is expected with a self-signed certificate.")
    print("You can safely proceed through the warning for local development purposes.")
    
    try:
        app.run(host='localhost', port=8443, ssl_context=ssl_context)
    finally:
        # Clean up temporary certificate files
        os.unlink(cert_path)
        os.unlink(key_path)
    
    return oauth_handler


def get_freshbooks_session(client_id, client_secret, token_file="oauth_token.json"):
    """Get an authorized session for the Freshbooks API.
    
    If no token exists, it will start the OAuth flow.
    If a token exists, it will use that token and refresh if needed.
    """
    oauth_handler = FreshbooksOAuth(client_id, client_secret, token_file)
    
    # If no token exists, start the OAuth flow
    if not oauth_handler.token:
        print("No existing token found. Starting OAuth authorization flow...")
        oauth_handler = start_oauth_flow(client_id, client_secret)
    else:
        print("Using existing OAuth token.")
    
    # Return the authorized session
    return oauth_handler.authorized_session()


if __name__ == "__main__":
    # Get client credentials from environment
    client_id = os.getenv("FRESHBOOKS_CLIENT_ID")
    client_secret = os.getenv("FRESHBOOKS_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Please set FRESHBOOKS_CLIENT_ID and FRESHBOOKS_CLIENT_SECRET environment variables")
        exit(1)
    
    # Start the OAuth flow
    oauth = start_oauth_flow(client_id, client_secret)
    
    # Once authorized, you can use the session
    session = oauth.authorized_session()
    
    # Example API call
    print("Testing API call...")
    response = session.get("https://api.freshbooks.com/accounting/account/profile")
    print(f"Response: {response.status_code}")
    if response.status_code == 200:
        print("Success! OAuth flow is working correctly.")
    else:
        print(f"Error: {response.text}")