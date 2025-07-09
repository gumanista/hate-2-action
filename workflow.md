## Step 1. problem_detector.py
Everything works fine here. We read the message from the messages table, make a LLM call to identify core problems and write them into the problems table. 


## Step 2. embed_and_match.py 


-- each run 
This script should work in the following way:
1. We take the problems from the problems table, which are not processed yet. (a flag "processed/not_processed" in the database table problems)
2. We create embeddings for the new problems whrere flag is "not_processed". 
3. Loop for each new problem: take a problem, compare its vector to the solutions vector, save top k problem-solution matches to the problems_solutions table.
4. Take the solution ids with the top n highest similarity and parse the projects from the projects_solutions table. Select the top m projects with the highest similarity scores. Save the project ids. 

Improvement is implemented: 
For each new post_solution detected in the first step: take the id of post_solution, compare post_solution vector to the projects table vectors, save top k post_solution-projects matches to the problems_solutions table.


-- the first run
1. create embeddings for the solutions and project tables and save them
2. match the projecs and solutions in the projects_solutions table. Loop through the projects: compare the vector of each project to the solutions vectors and write to the projects_solutions table top k. 



## Step 3. output_generator.py  
1. Take the message text from the messages table, change the flag to processed. Take the selected project ids from the previous step, and parse the relavant info about the selected projects from the projects table. 
2. Make an LLM call to generate the response. Save the response to the responses table 


Improvement is implemented:
Take the ids of projects selected based on the problems flow (take a problem, match with solution, extract the id of project from the projects_solution table). 
Take the ids of projects selected based on the post_solution approach (newly matched solutions to the projects) from the. Out of the selected projects select those with the highest similarity. 







## TELEGRAM BOT
The bot should take the message as an input in the json format and write it to the messages table. The bot should parse the output from the responses table. 


  
sqlite> .schema
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
CREATE TABLE messages (
  message_id        INTEGER PRIMARY KEY,
  user_id           INTEGER   NOT NULL,                -- original user ID
  user_username     TEXT      NOT NULL,                -- e.g. "alice123"
  
  chat_title        TEXT,                              -- e.g. group or channel name
  text              TEXT      NOT NULL,                -- the incoming message
  created_at        DATETIME  DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE responses (
  response_id    INTEGER PRIMARY KEY,                   -- unique ID for each reply
  message_id     INTEGER   NOT NULL REFERENCES messages(message_id),  
  text           TEXT      NOT NULL,                   -- the generated reply
  created_at     DATETIME  DEFAULT CURRENT_TIMESTAMP   -- when the reply was created
);
CREATE TABLE message_projects (
  message_id INTEGER NOT NULL REFERENCES messages(message_id),
  project_id INTEGER NOT NULL REFERENCES projects(project_id),
  PRIMARY KEY (message_id, project_id)
);
CREATE INDEX idx_problems_is_processed
  ON problems(is_processed);
CREATE INDEX idx_message_projects_message_id
  ON message_projects(message_id);