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
from flask import Flask, request, redirect, render_template_string, flash, url_for
from werkzeug.utils import secure_filename
import pandas as pd


from freshbooks.client import FreshbooksClient

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


def start_oauth_flow(client_id, client_secret, handle_csv=False):
    """
    Start the OAuth flow with a local HTTPS web server.
    
    Args:
        client_id: FreshBooks client ID
        client_secret: FreshBooks client secret
        handle_csv: If True, keep the server running for CSV uploads after authentication
    """
    oauth_handler = FreshbooksOAuth(client_id, client_secret)
    
    # Generate self-signed certificate for HTTPS
    cert_path, key_path = generate_self_signed_cert()
    ssl_context = (cert_path, key_path)
    
    # Create a simple Flask app to handle the callback
    app = Flask(__name__)
    app.secret_key = os.urandom(24)  # For flash messages
    
    # Create upload directory if it doesn't exist
    upload_folder = os.path.join(os.getcwd(), 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    app.config['UPLOAD_FOLDER'] = upload_folder
    
    # Global variable to track authentication status
    app.config['AUTHENTICATED'] = False
    app.config['OAUTH_HANDLER'] = oauth_handler
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    @app.route('/')
    def index():
        try:
            if app.config['AUTHENTICATED']:
                # Show file upload form after authentication
                return render_template_string('''
                    <!DOCTYPE html>
                    <html>
                        <head>
                            <title>Timeular to FreshBooks Integration</title>
                            <style>
                                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                                .container { max-width: 800px; margin: 0 auto; }
                                .form-group { margin-bottom: 20px; }
                                .btn { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; }
                                .success { background-color: #d4edda; border-color: #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                                .error { background-color: #f8d7da; border-color: #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                                .table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                                .table th, .table td { border: 1px solid #ddd; padding: 8px; }
                                .table th { background-color: #f2f2f2; }
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <h1>Timeular to FreshBooks Integration</h1>
                                
                                {% with messages = get_flashed_messages(with_categories=true) %}
                                    {% if messages %}
                                        {% for category, message in messages %}
                                            <div class="{{ category }}">{{ message }}</div>
                                        {% endfor %}
                                    {% endif %}
                                {% endwith %}
                                
                                <h2>Upload Timeular CSV Data</h2>
                                <form action="/upload" method="post" enctype="multipart/form-data">
                                    <div class="form-group">
                                        <label for="csvfile">Select CSV file:</label>
                                        <input type="file" id="csvfile" name="csvfile" accept=".csv,.xlsx,.xls" required>
                                    </div>
                                    <button type="submit" class="btn">Upload and Process</button>
                                </form>
                                
                                <h3>Instructions</h3>
                                <ol>
                                    <li>Export your time tracking data from Timeular</li>
                                    <li>Upload the CSV or Excel file using the form above</li>
                                    <li>The system will process the data and send it to FreshBooks</li>
                                </ol>
                                
                                {% if failed_entries %}
                                    <h3>Failed Time Entries</h3>
                                    <table class="table">
                                        <thead>
                                            <tr>
                                                <th>Time Entry</th>
                                                <th>Error</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for entry in failed_entries %}
                                                <tr>
                                                    <td>{{ entry.time_entry }}</td>
                                                    <td>{{ entry.error }}</td>
                                                </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                {% endif %}
                                
                                {% if fuzzy_matches %}
                                    <h3>Fuzzy Matches</h3>
                                    <table class="table">
                                        <thead>
                                            <tr>
                                                <th>Input</th>
                                                <th>Matched To</th>
                                                <th>Score</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for match in fuzzy_matches %}
                                                <tr>
                                                    <td>{{ match.input }}</td>
                                                    <td>{{ match.matched_to }}</td>
                                                    <td>{{ match.score }}</td>
                                                </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                {% endif %}
                            </div>
                        </body>
                    </html>
                ''', failed_entries=app.config.get('FAILED_ENTRIES', []), fuzzy_matches=app.config.get('FUZZY_MATCHES', []))
            else:
                # Start OAuth flow
                auth_url = oauth_handler.get_authorization_url()
                print(f"Opening browser to: {auth_url}")
                webbrowser.open(auth_url, new=1)
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
            
            # Set authentication status
            app.config['AUTHENTICATED'] = True
            
            if handle_csv:
                # Redirect to file upload interface
                return render_template_string('''
                    <html>
                        <head>
                            <title>Authorization Successful</title>
                            <style>
                                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                                .success { background-color: #d4edda; border-color: #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; }
                                .btn { display: inline-block; background: #0066cc; color: white; padding: 10px 20px; text-decoration: none; margin-top: 20px; border-radius: 5px; }
                            </style>
                            <meta http-equiv="refresh" content="3;url=/" />
                        </head>
                        <body>
                            <div class="success">
                                <h2>Authorization Successful!</h2>
                                <p>Token saved to file. You'll be redirected to the file upload page in a moment.</p>
                                <a href="/" class="btn">Go to File Upload</a>
                            </div>
                        </body>
                    </html>
                ''')
            else:
                # Shutdown the Flask server after successful authorization if not handling CSV
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
    
    @app.route('/upload', methods=['POST'])
    def upload_file():
        if request.method == 'GET':
            # If someone tries to access /upload directly with GET, just redirect to the main page
            return redirect('/')
        
        if not app.config['AUTHENTICATED']:
            return redirect('/')

        # Check if the post request has the file part
        if 'csvfile' not in request.files:
            flash('No file selected', 'error')
            return redirect('/')
            
        file = request.files['csvfile']
        
        # If user does not select a file, browser also submits an empty part
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect('/')
        
        try:
            # Save the file
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Process the file based on extension
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                flash('Unsupported file format. Please upload a CSV or Excel file.', 'error')
                return redirect('/')
                
            # Process the data and send to FreshBooks
            rows_processed, failed_entries, fuzzy_matches = process_timeular_data(df, app.config['OAUTH_HANDLER'])
            
            # Store failed entries and fuzzy matches in app config
            app.config['FAILED_ENTRIES'] = failed_entries
            app.config['FUZZY_MATCHES'] = fuzzy_matches
            
            flash(f'File processed successfully! {rows_processed} time entries uploaded to FreshBooks.', 'success')
            return redirect('/')
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            logging.error(f"Error processing file: {str(e)}")
            return redirect('/')
    
    print("\n" + "=" * 80)
    print("Starting local HTTPS server for OAuth callback...")
    print("NOTE: Your browser may show a security warning - this is expected with a self-signed certificate.")
    print("You can safely proceed through the warning for this local authentication process.")
    if handle_csv:
        print("\nAfter authentication, you'll be able to upload CSV files for processing.")
    print("=" * 80 + "\n")
    
    try:
        # Run the Flask app with SSL
        app.run(host='localhost', port=8443, ssl_context=ssl_context, debug=True)
    finally:
        # Clean up temporary certificate files if not handling CSV
        if not handle_csv:
            try:
                os.unlink(cert_path)
                os.unlink(key_path)
            except:
                pass
    
    return oauth_handler

# Add this function to process the uploaded data
def process_timeular_data(df, oauth_handler):
    """
    Process Timeular data and send to FreshBooks
    
    Args:
        df: Pandas DataFrame with time tracking data
        oauth_handler: OAuth handler for FreshBooks API
    
    Returns:
        Number of entries processed, list of failed entries, list of fuzzy matches
    """
    try:
        # Get an authorized session
        session = oauth_handler.authorized_session()
        
        # Get user's business ID
        response = session.get("https://api.freshbooks.com/auth/api/v1/users/me")
        user_data = response.json()
        
        # Assuming the first business membership is what we want
        business_id = user_data['response']['business_memberships'][0]['business']['id']
        
        # Initialize FreshBooks client
        client = FreshbooksClient(oauth_handler.token['access_token'])
        # Convert DataFrame columns to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Process each row
        failed_entries = []
        fuzzy_matches = []
        successful_entries = 0
        for _, row in df.iterrows():
            # Convert row to dictionary and clean up pandas types
            time_entry = {}
            for col, val in row.items():
                # Convert pandas Timestamp to ISO format string
                if hasattr(val, 'isoformat'):
                    time_entry[col] = val.isoformat()
                # Convert NaN/None values to empty string or None
                elif pd.isna(val):
                    time_entry[col] = None
                else:
                    time_entry[col] = val
            # print(time_entry)

            result = client.create_time_entry(time_entry)
            if result:
                successful_entries += 1
            else:
                logging.error(f"Error creating time entry: {result}")
                failed_entries.append({"time_entry": time_entry, "error": "Failed to create time entry"})
            
            # Collect fuzzy matches
            if 'fuzzy_matches' in result:
                fuzzy_matches.extend(result['fuzzy_matches'])
        
        return successful_entries, failed_entries, fuzzy_matches
        
    except Exception as e:
        logging.error(f"Error processing time entries: {str(e)}")
        raise


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
    oauth = start_oauth_flow(client_id, client_secret, handle_csv=True)
    
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