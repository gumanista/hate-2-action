# Hate-2-Action

This project leverages machine learning to analyze user messages, detect social or psychological problems, and recommend relevant projects based on those problems. It uses embeddings to match problems to solutions and solutions to projects, ultimately generating a helpful and empathetic response.

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- SQLite database
- OpenAI API Key (for LangChain integration)
- Required Python libraries (specified in `requirements.txt`)

### Installation Steps

1. **Clone the repository**:

    ```bash
    git clone <your-repository-url>
    cd <your-repository-directory>
    ```

2. **Create and activate a virtual environment**:

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install required dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up your OpenAI API Key**:

    Ensure you have set your OpenAI API Key in your environment variables:

    ```bash
    export OPENAI_API_KEY="your_openai_api_key"
    ```

    For Windows (using Command Prompt):

    ```bash
    set OPENAI_API_KEY="your_openai_api_key"
    ```

5. **Set up SQLite database**:

    Create an SQLite database (if not already created). You can specify your own database path by setting `DB_PATH` in the environment variables or directly in the script:

    ```bash
    export DB_PATH="path/to/your/database.db"
    ```

    Or for Windows (Command Prompt):

    ```bash
    set DB_PATH="path\\to\\your\\database.db"
    ```

    Run the script to create the necessary tables in the database:

    ```bash
    python3 cli.py init
    ```

6. **Run the first-time setup**:

    On the first run, you will need to precompute and save embeddings for the solutions, projects, and their relations (projects ↔ solutions).

    ```bash
    python3 cli.py init
    ```

## Database Schema

### Tables and Their Purpose

1. **`projects`**: Stores information about projects that can potentially solve the detected problems.
   - `project_id`: Unique identifier for the project.
   - `name`: Name of the project.
   - `description`: Description of the project.
   - `created_at`: Date and time when the project was added.
   - `website`: URL of the project’s website.
   - `contact_email`: Email for contacting the project.

2. **`problems`**: Stores the problems detected from user messages.
   - `problem_id`: Unique identifier for the problem.
   - `name`: The name of the problem.
   - `context`: The context or explanation for the problem.
   - `created_at`: Date and time when the problem was added.
   - `is_processed`: Flag indicating whether the problem has been processed or not.

3. **`solutions`**: Stores potential solutions that can address the problems.
   - `solution_id`: Unique identifier for the solution.
   - `name`: Name of the solution.
   - `context`: The context or description of the solution.
   - `created_at`: Date and time when the solution was added.

4. **`problems_solutions`**: Stores matches between problems and solutions, including similarity scores.
   - `problem_id`: Foreign key linking to the `problems` table.
   - `solution_id`: Foreign key linking to the `solutions` table.
   - `similarity_score`: The similarity score between the problem and the solution.

5. **`projects_solutions`**: Stores matches between projects and solutions, including similarity scores.
   - `project_id`: Foreign key linking to the `projects` table.
   - `solution_id`: Foreign key linking to the `solutions` table.
   - `similarity_score`: The similarity score between the project and the solution.

6. **`messages`**: Stores incoming user messages.
   - `message_id`: Unique identifier for the message.
   - `user_id`: The user who sent the message.
   - `user_username`: Username of the user.
   - `chat_title`: The title of the chat.
   - `text`: The content of the message.

7. **`responses`**: Stores generated responses to the user’s messages.
   - `response_id`: Unique identifier for the response.
   - `message_id`: The message the response corresponds to.
   - `text`: The generated response.
   - `created_at`: Date and time when the response was generated.

8. **`message_projects`**: Links messages to the recommended projects.
   - `message_id`: Foreign key linking to the `messages` table.
   - `project_id`: Foreign key linking to the `projects` table.

## How It Works

The system operates as follows:

### Step 1: Problem Detection
- The incoming message is analyzed using a pre-trained model (LangChain + OpenAI) to detect social or psychological problems mentioned in the message.
- These problems are stored in the `problems` table.

### Step 2: Embeddings & Matching
- Each problem, solution, and project is represented by an embedding (vector).
- For each unprocessed problem, the script computes an embedding, compares it with the embeddings of solutions, and stores the top `k` solutions in the `problems_solutions` table.
- Similarly, the script computes embeddings for projects and matches them to solutions, storing the top `k` projects in the `projects_solutions` table.

### Step 3: Generating a Response
- Once the problems and projects are matched, the script generates a response using LangChain's OpenAI model.
- The generated response is stored in the `responses` table, which is associated with the original user message.

## Running the Program

### 1. Running the Program for the First Time
To initialize the system and compute all embeddings for solutions, projects, and their relationships, run:

```bash
python3 cli.py init
```

### 2. Running the Program for the Second Time and Beyond
After running the first-time setup (`init`), you can run the program again with a new message. The program will detect problems from the message, match them to solutions and projects, and generate a response.

To insert a new message, detect problems, match solutions and projects, and generate a response, for example, use:

```bash
python3 cli.py run "Я б хотіла, щоб в нашому місті було менше безпритульних тварин." \
    --user-id 2345 \
    --username "kasia2000" \
    --chat-title "our_city"
```

### What Happens When You Run the Program:

1. **Insert the Message**: The text of the message is inserted into the `messages` table.

2. **Detect Problems**: The message is analyzed to detect problems (e.g., societal issues) using a pre-trained model.

3. **Match Solutions**: The problems are matched to potential solutions based on embeddings.

4. **Match Projects**: The matched solutions are further used to find relevant projects.

5. **Generate Response**: A response is generated based on the problems and projects, and stored in the `responses` table.

This command can be run multiple times with different messages. Each time, the problems, solutions, and projects will be matched and stored accordingly.

## Telegram Bot Integration

The project includes a Telegram bot that provides an interactive interface for users to access the system. The bot listens for messages that mention it and processes them using the same pipeline as the CLI interface.

### Features
- Responds to `/start` command with a welcome message and usage instructions
- Processes messages when the bot is mentioned (e.g., "@bot_name your message")
- Uses the same problem detection, solution matching, and response generation pipeline

### Running the Bot

1. Set up your Telegram Bot Token:
    ```bash
    export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
    ```

2. Run the bot:
    ```bash
    python3 -m src.telegram.bot
    ```

The bot will start listening for messages and process them using the project's main pipeline. Users can interact with the bot by mentioning it in their messages.



