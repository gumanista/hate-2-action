### TO-DO

check the project files to understand the project. this is a bot which suggests relevant donation organizations based on the problems  and solutions detected in the users message. I want alter the database to add the new table organization. the logic is as follows: each organization may have multiple projects running. check the todo.md to see the db schema

Database schema currently: 
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
sqlite> 



I have added 

-- 1) Create organizations table
CREATE TABLE organizations (
  organization_id   INTEGER PRIMARY KEY,
  name              TEXT      NOT NULL,
  description       TEXT,
  website           VARCHAR(255),
  contact_email     VARCHAR(255),
  created_at        DATETIME  DEFAULT CURRENT_TIMESTAMP
);

-- 2) Add FK to projects
ALTER TABLE projects
  ADD COLUMN organization_id INTEGER
    REFERENCES organizations(organization_id);

-- 3) Index the new FK
CREATE INDEX idx_projects_organization_id
  ON projects(organization_id);




