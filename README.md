# Timeular and Freshbooks Integration

This project integrates the Timeular API with Freshbooks to streamline time tracking and invoicing processes.

## Features

- Connects to the Timeular API to retrieve time entries.
- Creates invoices in Freshbooks based on time entries from Timeular.
- Provides a simple command-line interface to manage the integration.

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

3. Create a `.env` file based on the `.env.example` file and fill in your API keys and secrets.

## Usage

To run the integration, execute the following command:
```
pdm run python src/main.py
```

## Configuration

Make sure to set the following environment variables in your `.env` file:

- `TIMEULAR_API_KEY`: Your Timeular API key.
- `FRESHBOOKS_API_KEY`: Your Freshbooks API key.
- Any other required configuration settings.

## Testing

To run the tests, use:
```
pdm run pytest
```

## Contributing

Feel free to submit issues or pull requests for improvements and bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.