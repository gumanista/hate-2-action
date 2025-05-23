## Stages

### Stage 1: Problem Detector (`1_problem_detector.py`)

— Reads a social-media post from `message.txt`.
— Uses an LLM to extract deep social or psychological problems (name + context).
— Inserts or skips duplicates in the `problems` table of `donation.db`.
— Writes the list of detected problem IDs to `detected_problem_ids.json`.

### Stage 2: Embedding & Matching (`embed_and_match.py`)

This unified script replaces the previous Solution Detector and Project Detector steps.

— Loads `detected_problem_ids.json`.
— Connects to `donation.db`, enables the `vec0` extension, and creates three virtual tables:

* `problems_embeddings`
* `solutions_embeddings`
* `projects_embeddings`

— Fetches problem names, solution names, and project descriptions from the database.
— Generates OpenAI embeddings for each problem, solution, and project.
— Populates the three embedding tables with these vectors.
— Runs KNN searches:

1. **Problems → Solutions**: finds top‑K similar solutions per problem, upserting into `problems_solutions`.
2. **Projects → Solutions**: finds top‑K similar solutions per project, upserting into `projects_solutions`.

— (Optional) Writes out detected solution and project IDs to JSON:

* `detected_solution_ids.json`
* `detected_project_ids.json`

### Stage 3: Output Generator (`4_output_generator.py`)

— Reads the original `message.txt`, `detected_problem_ids.json`, and `detected_project_ids.json`.
— Fetches problem details and top 3–5 projects (by highest similarity score) from `donation.db`.
— Uses an LLM to generate a Ukrainian-language reply, summarizing problems and recommending projects (names, descriptions, contacts).
— Outputs the final response to stdout.

---

**Next Steps:**

* Rename `sqlite_vec_test.py` to `embed_and_match.py` and update its logic to optionally export detected IDs.
* Remove or archive `2_solution_detector.py` and `3_project_detector.py` to avoid confusion.
* Ensure documentation and CI scripts reference the new workflow.
