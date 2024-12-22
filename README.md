
# OpenAI o1 and o1 Mini- Discord Bot

## Overview

The **O1 Discord Bot** is a feature-rich OpenAI-powered assistant for Discord, offering token quotas, user history, custom prompts, and role-based access control. Users can interact with either the `o1` or `o1-mini` models to generate intelligent responses, all while adhering to daily quotas and rate limits. This bot is designed for high customization, ensuring that users and administrators can tailor the bot's behavior to fit their needs.

---

## Features

- **Custom Prompts**: Users can define their own prompts for tailored responses.
- **Mode Switching**: Toggle between `o1` (full power) or `mini` (lightweight) modes.
- **Daily Token Quotas**: Manage user quotas to control API usage effectively.
- **Rate Limiting**: Prevent spamming with configurable rate limits.
- **Role-Based Access Control**: Only users with a specific role can use the bot.
- **Usage Tracking**: Tracks token usage and stores it persistently.
- **Reset Mechanism**: Daily automatic reset for token usage.
- **Long Response Splitting**: Automatically splits long replies into multiple Discord embeds.
- **Help Commands**: Built-in help and guidance for users.

---

## Setup Instructions

### Prerequisites

1. **Python 3.8 or higher**: Install [Python](https://www.python.org/downloads/).
2. **Discord Bot Token**: Obtain a bot token from the [Discord Developer Portal](https://discord.com/developers/applications).
3. **OpenAI API Key**: Get your API key from the [OpenAI API Dashboard](https://platform.openai.com/).
4. **Environment Variables**: Create a `.env` file for secure configuration.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/o1-discord-bot.git
   cd o1-discord-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file:
   ```bash
   DISCORD_TOKEN=your_discord_bot_token
   OPENAI_API_KEY=your_openai_api_key
   ```

4. Configure `bot.py`:
   - Replace `ALLOWED_GUILD_ID` with your Discord server's ID.
   - Replace `REQUIRED_ROLE_ID` with the ID of the role allowed to use the bot.
   - (Optional) Customize `USER_QUOTAS` for specific users.

5. Run the bot:
   ```bash
   python bot.py
   ```

---

## Commands

### Main Command Group: `!o1`

| Command                 | Description                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| `!o1`                   | Show your current prompt and mode, or display help if no prompt is set.    |
| `!o1 <input>`           | Generate a response using your stored prompt and input.                    |
| `!o1 prompt <prompt>`   | Set a custom prompt for your interactions.                                 |
| `!o1 reset`             | Clear your current prompt.                                                 |
| `!o1 mode <o1|mini>`    | Switch between the `o1` (full) or `mini` (lightweight) mode.               |
| `!o1 help`              | Display detailed help information.                                         |

---

## Features in Detail

### **Token Quotas and Usage**
- Each user has a daily token quota defined in the `USER_QUOTAS` dictionary.
- Default quota (`DEFAULT_QUOTA`) applies to users not explicitly listed.
- Usage is tracked and stored persistently in `usage.json`.

### **Rate Limiting**
- Configurable rate limit (`RATE_LIMIT`) and time window (`TIME_WINDOW`).
- Prevents spam by enforcing a maximum number of requests per user within the defined window.

### **Custom Prompts and Modes**
- Users can set personalized prompts for contextual responses.
- Modes:
  - `o1`: Leverages `o1-preview` for comprehensive responses.
  - `mini`: Uses `o1-mini` for faster, lightweight interactions.

### **Role-Based Access**
- Only users with a specified role (`REQUIRED_ROLE_ID`) in the allowed guild (`ALLOWED_GUILD_ID`) can use the bot.

### **Response Handling**
- Long responses are split into multiple embeds to fit within Discord's character limits.
- Each embed includes token usage details in the footer.

---

## File Structure

- `bot.py`: Main bot logic and commands.
- `users.json`: Stores user-specific data (prompts and modes).
- `usage.json`: Tracks token usage for quota management.
- `.env`: Securely stores sensitive API keys and tokens.

---

## Contributing

1. Fork the repository.
2. Create a new branch: `git checkout -b feature-name`.
3. Commit your changes: `git commit -m 'Add feature-name'`.
4. Push to the branch: `git push origin feature-name`.
5. Submit a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Disclaimer

This bot interacts with OpenAI's API, and its usage is subject to [OpenAI's Terms of Service](https://openai.com/terms/). Monitor your API usage and costs accordingly.

---

## Support

For questions or feedback, feel free to open an issue on GitHub or contact me on Discord.

Happy coding! 🚀
