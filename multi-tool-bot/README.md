---

# Discord Bot

This is a Discord bot built using Python and the `discord.py` library. The bot includes several useful commands, such as creating polls, setting reminders, starting countdowns, predicting nationalities, showing emoji statistics, running daily trivia, searching for anime, and providing voice channel join alerts. 

## Features

- **Poll Command**: Create a poll with thumbs up and thumbs down reactions.
- **RemindMe Command**: Set a reminder that will notify you after a specified time.
- **Countdown Command**: Start a countdown timer and update the message every second.
- **Predict Command**: Predict the nationality based on the name.
- **EmojiStats Command**: Display the most used emojis in the channel.
- **DailyTrivia Command**: Participate in a daily trivia challenge.
- **Anime Command**: Search for an anime by title.
- **VoiceAlerts Command**: Subscribe or unsubscribe to alerts when users join a voice channel.
- **Error Handling**: Provides helpful instructions if a wrong command is entered.

## Commands

### Poll Command

Create a poll with a question. Users can react with 👍 or 👎.

```
!poll <question>
```

### RemindMe Command

Set a reminder. The bot will notify you after the specified time.

```
!remindme <time in seconds/minutes/hours> <reminder>
```

Examples of valid time formats: `30s`, `5m`, `1h`.

### Countdown Command

Start a countdown timer that updates the message every second.

```
!count <time in seconds/minutes/hours>
```

### Predict Command

Predict the nationality based on a given name.

```
!predict <name>
```

### EmojiStats Command

Show the most used emojis in the current channel.

```
!emojistats
```

### DailyTrivia Command

Participate in a daily trivia challenge.

```
!dailytrivia
```

### Anime Command

Search for an anime by title.

```
!anime <title>
```

### VoiceAlerts Command

Subscribe or unsubscribe to alerts when users join a voice channel.

```
!voicealerts <subscribe/unsubscribe>
```

## Getting Started

### Prerequisites

- Python 3.6 or higher
- `discord.py` library
- `python-dotenv` library
- `aiohttp` library

### Installation

1. Clone the repository:

```sh
git clone https://github.com/mehedisardar/discord-bot.git
cd your-repository
```

2. Create a virtual environment and activate it:

```sh
python -m venv env
source env/bin/activate  # On Windows use `env\Scripts\activate`
```

3. Install the required packages:

```sh
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory and add your Discord bot token:

```
DISCORD_TOKEN=your_discord_bot_token
```

### Running the Bot

Run the bot using the following command:

```sh
python bot.py
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [discord.py](https://discordpy.readthedocs.io/en/stable/) - Python wrapper for the Discord API
- [dotenv](https://pypi.org/project/python-dotenv/) - Read environment variables from a .env file
- [aiohttp](https://docs.aiohttp.org/en/stable/) - Asynchronous HTTP client/server framework for Python

---
