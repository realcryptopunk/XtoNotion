#!/bin/bash

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "Heroku CLI is not installed. Please install it first: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if user is logged in to Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "You are not logged in to Heroku. Please run 'heroku login' first."
    exit 1
fi

# Get app name from command line or prompt
if [ -z "$1" ]; then
    read -p "Enter your Heroku app name: " APP_NAME
else
    APP_NAME=$1
fi

# Check if app exists, if not create it
if ! heroku apps:info --app $APP_NAME &> /dev/null; then
    echo "Creating new Heroku app: $APP_NAME"
    heroku create $APP_NAME
else
    echo "Using existing Heroku app: $APP_NAME"
fi

# Check if .env file exists
if [ -f .env ]; then
    echo "Found .env file. Setting environment variables from it..."
    
    # Read .env file and set environment variables
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ $key =~ ^#.*$ ]] || [[ -z $key ]]; then
            continue
        fi
        
        # Remove quotes from value if present
        value=$(echo $value | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
        
        echo "Setting $key..."
        heroku config:set $key=$value --app $APP_NAME
    done < .env
else
    echo "No .env file found. Please set environment variables manually:"
    echo "heroku config:set TELEGRAM_BOT_TOKEN=your_token --app $APP_NAME"
    echo "heroku config:set OPENAI_API_KEY=your_key --app $APP_NAME"
    echo "heroku config:set NOTION_API_KEY=your_key --app $APP_NAME"
    echo "heroku config:set NOTION_DATABASE_ID=your_id --app $APP_NAME"
fi

# Deploy to Heroku
echo "Deploying to Heroku..."
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# Start the worker dyno
echo "Starting the worker dyno..."
heroku ps:scale worker=1 --app $APP_NAME

# Install Playwright browsers
echo "Installing Playwright browsers..."
heroku run python -m playwright install --app $APP_NAME

echo "Deployment complete! Check the logs with: heroku logs --tail --app $APP_NAME" 