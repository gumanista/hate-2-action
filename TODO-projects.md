
## TODO Adding subprojects

Each project in the database may or may not have few child subprojects. Add the tables subprojects and projects_subprojects to store the matching which will have to be done manually. DONE


The core logic of matching:
Tables projects, subprojects and projects_subprojects (which connects the previous two) are filled matually. 


First run of the program:
Match solutions to subprojects first, and then match the projects with no subprojects (use projects_subprojects table to navigate). Save the results to the projects_solutions table. The table projects_solutions should include the project id, subproject id or NULL (if a project doesnt have subprojects), solution id etc.   

Next runs of the program:
Step 1. 
The generaled by LLM problems are writen to the problems table. 
The generaled by LLM solutions are writen to the solutions table. 

Step 2. 
We match new problems to the solutions (all at once), the results are written to the problems_solutions table.
We also match new solutions to the projects as describes before.

Step 3. Navigate to the relavant projects, no changes in the logic 



2. Update and create the style response for the chatbot 
- add the telegram bottoms to select the style response at the beginning 
- it is possible to change the style later 
- the style should be saved for each user in the database


3. Create a simple user interface using HTML and CSS to add the projects and their subprojects 



















Database schema currently: 

CREATE TABLE projects (
  project_id    INTEGER PRIMARY KEY,
  name          TEXT       NOT NULL,
  description   TEXT,
  created_at    DATETIME   DEFAULT CURRENT_TIMESTAMP
, website VARCHAR(255), contact_email VARCHAR(255));
CREATE TABLE problems (
  problem_id    INTEGER PRIMARY KEY,
  name          TEXT       NOT NULL,
  context       TEXT,
  created_at    DATETIME   DEFAULT CURRENT_TIMESTAMP
, is_processed INTEGER DEFAULT 0);
CREATE TABLE solutions (
  solution_id   INTEGER PRIMARY KEY,
  name          TEXT       NOT NULL,
  context       TEXT,
  created_at    DATETIME   DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE problems_solutions (
  problem_id       INTEGER NOT NULL REFERENCES problems(problem_id),
  solution_id      INTEGER NOT NULL REFERENCES solutions(solution_id),
  similarity_score REAL    NOT NULL,
  matched_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (problem_id, solution_id)
);
CREATE TABLE projects_solutions (
  project_id       INTEGER NOT NULL REFERENCES projects(project_id),
  solution_id      INTEGER NOT NULL REFERENCES solutions(solution_id),
  similarity_score REAL    NOT NULL,
  matched_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (project_id, solution_id)
);
CREATE TABLE IF NOT EXISTS "_messages_old" (
  message_id        INTEGER PRIMARY KEY,
  user_id           INTEGER   NOT NULL,                -- original user ID
  user_username     TEXT      NOT NULL,                -- e.g. "alice123"
  
  chat_title        TEXT,                              -- e.g. group or channel name
  text              TEXT      NOT NULL,                -- the incoming message
  created_at        DATETIME  DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE responses (
  response_id    INTEGER PRIMARY KEY,                   -- unique ID for each reply
  message_id     INTEGER   NOT NULL REFERENCES "_messages_old"(message_id),  
  text           TEXT      NOT NULL,                   -- the generated reply
  created_at     DATETIME  DEFAULT CURRENT_TIMESTAMP   -- when the reply was created
);
CREATE TABLE message_projects (
  message_id INTEGER NOT NULL REFERENCES "_messages_old"(message_id),
  project_id INTEGER NOT NULL REFERENCES projects(project_id),
  PRIMARY KEY (message_id, project_id)
);
CREATE INDEX idx_problems_is_processed
  ON problems(is_processed);
CREATE INDEX idx_message_projects_message_id
  ON message_projects(message_id);
CREATE VIRTUAL TABLE vec_solutions
        USING vec0(
            solution_id   INTEGER PRIMARY KEY,
            embedding     float[1536]
        );
CREATE TABLE IF NOT EXISTS "vec_solutions_info" (key text primary key, value any);
CREATE TABLE IF NOT EXISTS "vec_solutions_chunks"(chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,size INTEGER NOT NULL,validity BLOB NOT NULL,rowids BLOB NOT NULL);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE IF NOT EXISTS "vec_solutions_rowids"(rowid INTEGER PRIMARY KEY AUTOINCREMENT,id,chunk_id INTEGER,chunk_offset INTEGER);
CREATE TABLE IF NOT EXISTS "vec_solutions_vector_chunks00"(rowid PRIMARY KEY,vectors BLOB NOT NULL);
CREATE VIRTUAL TABLE vec_projects
        USING vec0(
            project_id    INTEGER PRIMARY KEY,
            embedding     float[1536]
        );
CREATE TABLE IF NOT EXISTS "vec_projects_info" (key text primary key, value any);
CREATE TABLE IF NOT EXISTS "vec_projects_chunks"(chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,size INTEGER NOT NULL,validity BLOB NOT NULL,rowids BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS "vec_projects_rowids"(rowid INTEGER PRIMARY KEY AUTOINCREMENT,id,chunk_id INTEGER,chunk_offset INTEGER);
CREATE TABLE IF NOT EXISTS "vec_projects_vector_chunks00"(rowid PRIMARY KEY,vectors BLOB NOT NULL);
CREATE VIRTUAL TABLE vec_problems
        USING vec0(
            problem_id    INTEGER PRIMARY KEY,
            embedding     float[1536]
        );
CREATE TABLE IF NOT EXISTS "vec_problems_info" (key text primary key, value any);
CREATE TABLE IF NOT EXISTS "vec_problems_chunks"(chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,size INTEGER NOT NULL,validity BLOB NOT NULL,rowids BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS "vec_problems_rowids"(rowid INTEGER PRIMARY KEY AUTOINCREMENT,id,chunk_id INTEGER,chunk_offset INTEGER);
CREATE TABLE IF NOT EXISTS "vec_problems_vector_chunks00"(rowid PRIMARY KEY,vectors BLOB NOT NULL);
CREATE TABLE users (
  user_id    INTEGER PRIMARY KEY,
  username   TEXT      NOT NULL,
  first_name TEXT,
  last_name  TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE chats (
  chat_id    INTEGER PRIMARY KEY,
  chat_title TEXT,
  chat_type  TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE messages (
  message_id    INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(user_id),
  chat_id       INTEGER REFERENCES chats(chat_id),
  text          TEXT    NOT NULL,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_preferences (
  user_id       INTEGER PRIMARY KEY REFERENCES users(user_id),
  style         TEXT      NOT NULL DEFAULT 'empathetic',
  updated_at    DATETIME  DEFAULT CURRENT_TIMESTAMP
);