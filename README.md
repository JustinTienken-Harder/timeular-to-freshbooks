# Timeular and Freshbooks Integration

This project integrates the Timeular API with Freshbooks and WaveApp to streamline time tracking and invoicing processes.

## Features

### FreshBooks Integration (Original)
- Connects to the Timeular API to retrieve time entries.
- Creates invoices in Freshbooks based on time entries from Timeular.
- Provides a simple command-line interface to manage the integration.

### WaveApp Integration (New!)
- **Browser-based interface** for uploading Timeular CSV exports
- **Interactive matching** of activities to WaveApp customers and tags to services
- **Automatic invoice generation** with consolidated time entries
- **Note aggregation** - combines all time entry notes for each service
- **Smart pricing** - uses WaveApp product pricing (ignores Timeular rates)

## Prerequisites

### Installing Python

If you don't have Python installed on your computer:

#### For Windows:
1. Download the latest Python installer from [python.org](https://www.python.org/downloads/)
2. Run the installer and make sure to check "Add Python to PATH" during installation
3. Verify installation by opening Command Prompt and typing `python --version`

#### For Mac:
1. Install Homebrew if you don't have it:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Install Python using Homebrew:
   ```
   brew install python
   ```
3. Verify installation by opening Terminal and typing `python3 --version`

#### For Linux:
Most Linux distributions come with Python pre-installed. If not:
```
sudo apt update
sudo apt install python3 python3-pip
```

### Installing PDM (Python Dependency Manager)

PDM is a modern Python package manager that we use to manage dependencies.

#### For Windows:
```
pip install pdm
```

#### For Mac/Linux:
```
pip3 install pdm
```
If this doesnt work try `brew install pdm`

Verify PDM installation:
```
pdm --version
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/timeular-freshbooks-integration.git
   cd timeular-freshbooks-integration
   ```

2. Install dependencies using PDM:
   ```
   pdm install
   ```

3. Create a .env file based on the .env.example file:
   ```
   cp .env.example .env
   ```
   Then edit the .env file with your text editor and fill in your API keys and secrets.

## Usage

### Option 1: WaveApp Integration (Recommended)

1. Start the Flask web server:
   ```
   pdm run python src/waveapp_server.py
   ```

2. Open your browser to `http://localhost:5001`

3. Follow the workflow:
## Configuration

Make sure to set the following environment variables in your .env file:

### WaveApp Configuration (for WaveApp integration)
- `WAVEAPP_API_TOKEN`: Your WaveApp API token
- `WAVEAPP_BUSINESS_ID`: Your WaveApp business ID
- `FLASK_SECRET_KEY`: Random secret key for Flask sessions

### Timeular Configuration
- `TIMEULAR_API_KEY`: Your Timeular API key
- `TIMEULAR_API_SECRET`: Your Timeular API secret

### FreshBooks Configuration (for FreshBooks integration)
- `FRESHBOOKS_CLIENT_ID`: Your Freshbooks OAuth client ID
- `FRESHBOOKS_CLIENT_SECRET`: Your Freshbooks OAuth client secret
- `FRESHBOOKS_BUSINESS_ID`: Your Freshbooks business ID (found in account settings)

### Getting WaveApp API Credentials

1. Log in to your WaveApp account
2. Go to **Settings** → **API Access**
3. Create a new API token (Full Access or Invoice Management)
4. Copy your API token and Business ID
5. Add them to your `.env` file
```
pdm run python src/main.py
```

The application will guide you through:
- Authentication with both services
- Choosing between CSV import or direct Timeular API connection
- Submitting time entries to Freshbooks

## Configuration

Make sure to set the following environment variables in your .env file:

- `TIMEULAR_API_KEY`: Your Timeular API key
- `TIMEULAR_API_SECRET`: Your Timeular API secret
- `FRESHBOOKS_CLIENT_ID`: Your Freshbooks OAuth client ID
- `FRESHBOOKS_CLIENT_SECRET`: Your Freshbooks OAuth client secret
- `FRESHBOOKS_BUSINESS_ID`: Your Freshbooks business ID (found in account settings)

## Troubleshooting

- **"Command not found" errors**: Make sure Python and PDM are correctly added to your PATH
- **Authentication issues**: Verify your API keys and secrets in the .env file
- **PDM installation problems**: Try using `python -m pip install pdm` instead

## Testing

To run the tests, use:
```
pdm run pytest
```

## Contributing

Feel free to submit issues or pull requests for improvements and bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.