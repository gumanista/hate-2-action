# Project Description

This project processes social media posts to identify underlying social or psychological problems, find relevant solutions and projects, and generate a tailored response. The workflow is divided into three main stages: Problem Detection, Embedding & Matching, and Output Generation.

## Functionalities and Workflow

The project processes a social media post from `message.txt` through a pipeline involving several Python scripts and a SQLite database (`donation.db`) with the `vec0` extension for vector embeddings.

### Stage 1: Problem Detector (`src/problem_detector.py`)

- **Input:** Reads a social media post from [`message.txt`](message.txt).
- **Process:**
    - Utilizes a Large Language Model (LLM) to analyze the post and extract deep social or psychological problems, identifying both the problem name and its context within the message.
    - Checks for duplicate problems in the `problems` table of the `donation.db` database and inserts new, unique problems.
- **Output:** Writes a list of detected problem IDs to `detected_problem_ids.json`.

### Stage 2: Embedding & Matching (`src/embed_and_match.py`)

- **Input:**
    - Loads detected problem IDs from `detected_problem_ids.json`.
    - Fetches problem names, solution names, and project descriptions from the `donation.db` database.
- **Process:**
    - Connects to `donation.db` and enables the `vec0` extension.
    - Creates three virtual tables for storing embeddings: `problems_embeddings`, `solutions_embeddings`, and `projects_embeddings`.
    - Generates OpenAI embeddings for the fetched problems, solutions, and projects.
    - Populates the respective embedding tables with the generated vectors.
    - Performs K-Nearest Neighbors (KNN) searches to find similarities:
        1. **Problems to Solutions:** Finds the top-K most similar solutions for each detected problem and upserts the relationships into the `problems_solutions` table.
        2. **Projects to Solutions:** Finds the top-K most similar solutions for each project and upserts the relationships into the `projects_solutions` table.
- **Output:** Optionally writes detected solution and project IDs to `detected_solution_ids.json` and `detected_project_ids.json`.

### Stage 3: Output Generator (`src/output_generator.py`)

- **Input:**
    - Reads the original social media post from [`message.txt`](message.txt).
    - Reads detected problem IDs from `detected_problem_ids.json`.
    - Reads detected project IDs from `detected_project_ids.json`.
- **Process:**
    - Fetches detailed information about the detected problems and the top 3-5 most similar projects (based on similarity scores from Stage 2) from `donation.db`.
    - Uses a Large Language Model (LLM) to generate a response in Ukrainian.
    - The response summarizes the identified problems and recommends the relevant projects, including their names, descriptions, and contact information.
- **Output:** Prints the final generated response to standard output.

## How Everything is Computed

The core computations involve:

1.  **LLM-based Problem Extraction:** An LLM analyzes text to identify and categorize problems.
2.  **Embedding Generation:** OpenAI's embedding model converts text data (problem names, solution names, project descriptions) into numerical vectors that capture semantic meaning.
3.  **Vector Similarity Search (KNN):** The `vec0` extension in SQLite is used to perform efficient K-Nearest Neighbors searches on the embedding vectors. This allows the project to find the most semantically similar solutions for identified problems and the most similar solutions associated with projects. The similarity scores from these searches are crucial for ranking and selecting the most relevant projects in the final stage.
4.  **LLM-based Response Generation:** A final LLM is used to synthesize the original message, detected problems, and relevant project information into a coherent and helpful response in Ukrainian.

This workflow ensures that the project can automatically process social media posts, understand the underlying issues, and connect users with potentially relevant projects or solutions based on semantic similarity.