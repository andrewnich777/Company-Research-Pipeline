# Anthropic API Key Configuration

**IMPORTANT: Never commit API keys to version control.**

## Setup

1. Create a `.env` file in the project root (this file is gitignored)
2. Add your API key:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

## Usage

```bash
# Option 1: Using environment variable (recommended)
export ANTHROPIC_API_KEY=your-api-key-here
python main.py stripe.com

# Option 2: Using .env file (auto-loaded if python-dotenv is installed)
python main.py stripe.com

# Option 3: Command line argument (not recommended for production)
python main.py stripe.com --api-key your-api-key-here
```

## Getting an API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and store it securely

## Security Best Practices

- Never share your API key publicly
- Use environment variables in production
- Rotate keys periodically
- Use separate keys for development and production
