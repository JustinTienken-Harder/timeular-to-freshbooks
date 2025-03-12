import os
import json
import webbrowser
import ssl
import tempfile
import logging
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect

def generate_self_signed_cert():
    """Generate a self-signed certificate for HTTPS."""
    # Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Create a self-signed certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Timeular Freshbooks Integration"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
        critical=False,
    ).sign(key, hashes.SHA256())
    
    # Write the cert and key to temporary files
    cert_file = tempfile.NamedTemporaryFile(delete=False)
    key_file = tempfile.NamedTemporaryFile(delete=False)
    
    cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
    key_file.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))
    
    cert_file.close()
    key_file.close()
    
    return cert_file.name, key_file.name

class FreshbooksOAuth:
    """OAuth2 handler for Freshbooks API with HTTPS support."""
    
    # Freshbooks OAuth endpoints
    AUTH_URL = "https://my.freshbooks.com/service/auth/oauth/authorize"
    TOKEN_URL = "https://api.freshbooks.com/auth/oauth/token"
    REDIRECT_URI = "https://localhost:8443/callback"  # Use HTTPS for production
    
    def __init__(self, client_id, client_secret, token_file="oauth_token.json"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = token_file
        self.token = self._load_token()
        self.state = None
        
        # Create OAuth session
        self.oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.REDIRECT_URI,
        )
    
    def make_new_session_with_state(self):
        """Create a new OAuth session with a new state."""
        current_state = self.state
        self.oauth = OAuth2Session(
            self.client_id,
            token = current_state, 
            redirect_uri=self.REDIRECT_URI,
        )
        self.oauth.headers.update({
            'User-Agent': 'FreshBooks API (python) 1.0.0',
            'Content-Type': 'application/json'
        })
    
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
        self.state = state
        return authorization_url
    
    def fetch_token(self, full_url):
        """Exchange the authorization code for an access token."""
        print(f"Got the full url: {full_url}")
        self.make_new_session_with_state()
        token = self.oauth.fetch_token(
            self.TOKEN_URL,
            client_secret = self.client_secret,
            authorization_response = full_url
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


def start_oauth_flow(client_id, client_secret):
    """Start the OAuth flow with a local HTTPS web server."""
    oauth_handler = FreshbooksOAuth(client_id, client_secret)
    
    # Generate self-signed certificate for HTTPS
    cert_path, key_path = generate_self_signed_cert()
    ssl_context = (cert_path, key_path)
    
    # Create a simple Flask app to handle the callback
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    @app.route('/')
    def index():
        try:
            # Properly unpack the tuple returned from get_authorization_url()
            auth_url = oauth_handler.get_authorization_url()
            print(f"Opening browser to: {auth_url}")
            webbrowser.open(auth_url, new = 1)
            return "Opened browser for authorization. Please check your browser window and approve the access request."
        except Exception as e:
            logging.error(f"Error generating authorization URL: {str(e)}")
            return f"Error: {str(e)}"
    
    @app.route('/callback')
    def callback():
        try:
            # Get the full URL including the authorization code
            full_url = request.url
            
            # If behind a proxy, it might not have the scheme
            if not full_url.startswith('https'):
                full_url = 'https://' + request.host + request.full_path
                print("Detected proxy, using HTTPS scheme.")
                
            print(f"Callback received: {full_url}")
            
            # Exchange the authorization code for an access token
            token = oauth_handler.fetch_token(full_url)
            print("Token successfully obtained!")
            
            # Shutdown the Flask server after successful authorization
            def shutdown():
                request.environ.get('werkzeug.server.shutdown')()
            
            # Use a separate thread to shutdown the server
            import threading
            threading.Timer(1, lambda: os._exit(0)).start()
            
            return """
            <html>
                <head>
                    <title>Authorization Successful</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                        .success { background-color: #d4edda; border-color: #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; }
                    </style>
                </head>
                <body>
                    <div class="success">
                        <h2>Authorization Successful!</h2>
                        <p>Token saved to file. You can close this window and return to the application.</p>
                    </div>
                </body>
            </html>
            """
        except Exception as e:
            logging.error(f"Error in callback: {str(e)}")
            return f"""
            <html>
                <head>
                    <title>Authorization Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                        .error {{ background-color: #f8d7da; border-color: #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; }}
                    </style>
                </head>
                <body>
                    <div class="error">
                        <h2>Authorization Error</h2>
                        <p>Error during authorization: {str(e)}</p>
                        <p>Please close this window and try again.</p>
                    </div>
                </body>
            </html>
            """
    
    print("\n" + "=" * 80)
    print("Starting local HTTPS server for OAuth callback...")
    print("NOTE: Your browser may show a security warning - this is expected with a self-signed certificate.")
    print("You can safely proceed through the warning for this local authentication process.")
    print("=" * 80 + "\n")
    
    try:
        # Run the Flask app with SSL
        app.run(host='localhost', port=8443, ssl_context=ssl_context, debug=False)
    finally:
        # Clean up temporary certificate files
        try:
            os.unlink(cert_path)
            os.unlink(key_path)
        except:
            pass
    
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