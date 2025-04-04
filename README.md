# XToNotion Bot

A Telegram bot that extracts content from Twitter/X and websites, analyzes it with AI, and saves it to your Notion database.

## Features

- Extract and analyze tweets from Twitter/X
- Extract and analyze content from websites
- AI-powered categorization and insights
- Save entries to your Notion database
- Enhanced summaries with key points and action items

## Deployment to Heroku

### Prerequisites

- [Heroku account](https://signup.heroku.com/)
- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
- [Git](https://git-scm.com/)

### Environment Variables

You need to set the following environment variables in Heroku:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `OPENAI_API_KEY`: Your OpenAI API key
- `NOTION_API_KEY`: Your Notion API key
- `NOTION_DATABASE_ID`: Your Notion database ID

### Deployment Steps

1. **Install the Heroku CLI and login**:
   ```bash
   # Install Heroku CLI (if not already installed)
   # Login to Heroku
   heroku login
   ```

2. **Create a new Heroku app**:
   ```bash
   heroku create your-app-name
   ```

3. **Set up environment variables**:
   ```bash
   heroku config:set TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   heroku config:set OPENAI_API_KEY=your_openai_api_key
   heroku config:set NOTION_API_KEY=your_notion_api_key
   heroku config:set NOTION_DATABASE_ID=your_notion_database_id
   ```

4. **Deploy your code**:
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push heroku main
   ```

5. **Start the worker dyno**:
   ```bash
   heroku ps:scale worker=1
   ```

6. **Check the logs**:
   ```bash
   heroku logs --tail
   ```

### Troubleshooting

- If you encounter issues with Playwright, you may need to install the browser dependencies:
  ```bash
  heroku run python -m playwright install
  ```

- If the bot is not responding, check the logs for errors:
  ```bash
  heroku logs --tail
  ```

## Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your API keys
4. Run the bot: `python main.py --bot`

## License

MIT 