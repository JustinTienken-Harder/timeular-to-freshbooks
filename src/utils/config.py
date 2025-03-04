import os
from dotenv import load_dotenv, find_dotenv

from freshbooks.authentication import get_freshbooks_session
# Try to find .env file in parent directories if not in current directory
dotenv_path = find_dotenv()
if dotenv_path:
    print(f"Found .env file at: {dotenv_path}")
    success = load_dotenv(dotenv_path)
    print(f"Loading .env file: {'Success' if success else 'Failed'}")
else:
    print("No .env file found!")
    success = load_dotenv()

print(f"Current working directory: {os.getcwd()}")

class Config:
    TIMEULAR_API_KEY = os.getenv("TIMEULAR_API_KEY")
    TIMEULAR_API_SECRET = os.getenv("TIMEULAR_API_SECRET")
    FRESHBOOKS_CLIENT_ID = os.getenv("FRESHBOOKS_CLIENT_ID")
    FRESHBOOKS_CLIENT_SECRET  = os.getenv("FRESHBOOKS_CLIENT_SECRET")
    FRESHBOOKS_USER_ID = os.getenv("FRESHBOOKS_USER_ID") # Optional
    
    @staticmethod
    def validate():
        missing_vars = []
        if not Config.TIMEULAR_API_KEY:
            missing_vars.append("TIMEULAR_API_KEY")
        if not Config.TIMEULAR_API_SECRET:
            missing_vars.append("TIMEULAR_API_SECRET")
        if not Config.FRESHBOOKS_CLIENT_ID:
            missing_vars.append("FRESHBOOKS_CLIENT_ID")
        if not Config.FRESHBOOKS_CLIENT_ID:
            missing_vars.append("FRESHBOOKS_CLIENT_ID")
        
        if missing_vars:
            raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")
        return True
    
    def get_freshbooks_session(self):
        """Get an authorized Freshbooks API session."""
        self.session = get_freshbooks_session(
            client_id=Config.FRESHBOOKS_CLIENT_ID,
            client_secret=Config.FRESHBOOKS_CLIENT_SECRET
        )
        return self.session
    
    def get_freshbooks_token(self):
        """Get the Freshbooks API token."""
        if not self.session:
            self.get_freshbooks_session()
        return self.session.token

def load_config():
    configs = Config()
    if configs.validate():
        return {
            "TIMEULAR_API_KEY": configs.TIMEULAR_API_KEY,
            "TIMEULAR_API_SECRET": configs.TIMEULAR_API_SECRET,
            "FRESHBOOKS_CLIENT_ID": configs.FRESHBOOKS_CLIENT_ID,
            "FRESHBOOKS_CLIENT_SECRET": configs.FRESHBOOKS_CLIENT_SECRET,
        }
    

if __name__ == "__main__":
    configurations = Config()
    print(configurations.TIMEULAR_API_KEY)
    try:
        if configurations.validate():
            print("All required environment variables are present.")
            # Print values with partial masking for security
            print(f"TIMEULAR_API_KEY: {Config.TIMEULAR_API_KEY[:4]}..." if Config.TIMEULAR_API_KEY else "Not set")
            print(f"TIMEULAR_API_SECRET: {Config.TIMEULAR_API_SECRET[:4]}..." if Config.TIMEULAR_API_SECRET else "Not set")
            print(f"FRESHBOOKS_CLIENT_ID: {Config.FRESHBOOKS_CLIENT_ID[:4]}..." if Config.FRESHBOOKS_CLIENT_ID else "Not set")
    except ValueError as e:
        print(f"Configuration error: {e}")