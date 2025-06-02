# Project Title (Replace with actual title)

This project implements a Telegram bot that processes user messages, identifies potential problems or needs, and suggests relevant projects or resources based on the message content.

## Features

*   **Problem Detection:** Analyzes incoming messages to identify specific problems or requirements.
*   **Embedding Matching:** Uses embeddings to find and match relevant projects or resources from a database (`donation.db`).
*   **Output Generation:** Generates a coherent and helpful reply to the user based on the detected problems and matched projects.
*   **Telegram Integration:** Operates as a Telegram bot, interacting with users via messages.

## Workflow

The core workflow is handled by the `src/pipeline.py` module. When a message is received by the Telegram bot:

1.  The message is processed to **detect problems** or needs mentioned by the user.
2.  Based on the detected problems, **embeddings are computed and matched** against a database of projects (`donation.db`) to find the most relevant ones.
3.  A final **reply is generated** using the original message, detected problems, and matched projects. This reply is then sent back to the user via Telegram.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **Install dependencies:**
    Make sure you have Python 3.6+ installed.
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up the Telegram Bot Token:**
    Obtain a bot token from the BotFather on Telegram. Set it as an environment variable:
    ```bash
    export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
    ```
    Replace `"YOUR_BOT_TOKEN"` with your actual token.

4.  **Database:**
    Ensure the `donation.db` file exists in the project root directory. This database is used to store information for problem detection and project matching. (Further instructions on populating or managing the database may be needed depending on the project setup).

## Usage

To run the Telegram bot, execute the following command from the project root directory:

```bash
python3 -m src.telegram.bot
```

This will start the bot, and it will begin polling for new messages.

## Project Structure

*   `cli.py`: Command-line interface entry point (if applicable).
*   `requirements.txt`: Lists project dependencies.
*   `donation.db`: The SQLite database file used by the project.
*   `src/`: Contains the main source code.
    *   `__init__.py`: Initializes the `src` package.
    *   `embed_and_match.py`: Handles embedding computation and matching.
    *   `output_generator.py`: Generates the final bot reply.
    *   `pipeline.py`: Orchestrates the main workflow.
    *   `problem_detector.py`: Detects problems in user messages.
    *   `telegram/`: Contains Telegram bot specific code.
        *   `__init__.py`: Initializes the `telegram` package.
        *   `bot.py`: The main Telegram bot application.
        *   `config.py`: Configuration settings for the bot (e.g., token).
        *   `handlers.py`: Defines handlers for Telegram messages and commands.