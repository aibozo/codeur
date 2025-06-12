#\!/bin/bash
echo "🤖 Agent Environment Setup"
echo "========================="
echo

if [ -f .env ]; then
    echo "✓ .env file already exists"
else
    if [ -f .env.example ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo "✓ Created .env file"
        echo
        echo "⚠️  Please edit .env and add your OpenAI API key"
        echo "   Open .env and replace 'your-openai-api-key-here' with your actual key"
    else
        echo "❌ .env.example not found"
        exit 1
    fi
fi

echo
echo "To use the agent:"
echo "1. Make sure your OpenAI API key is in the .env file"
echo "2. Run: poetry run agent --help"
echo
echo "Example commands:"
echo "  poetry run agent plan \"Add error handling to the API\""
echo "  poetry run agent explain \"How does the authentication work?\""
echo "  poetry run agent search \"fetch_data function\""
echo

if [ -f .env ]; then
    if grep -q "your-openai-api-key-here" .env; then
        echo "⚠️  WARNING: You still need to add your OpenAI API key to .env"
    elif grep -q "OPENAI_API_KEY=" .env; then
        echo "✓ OpenAI API key appears to be configured in .env"
    fi
fi
EOF < /dev/null
