import os
import sys
import psycopg2
from langchain_openai import OpenAIEmbeddings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server.database import Database

def main():
    """Main function to rebuild vector embeddings."""
    with Database() as db:
        print("Rebuilding vector embeddings...")
        embedder = OpenAIEmbeddings()
        
        # --- Solutions ---
        cur = db.conn.cursor()

        # --- Solutions ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vec_solutions (
                solution_id INTEGER PRIMARY KEY,
                embedding vector(1536)
            );
        """)
        
        cur.execute("SELECT solution_id, context FROM solutions;")
        rows_to_embed = cur.fetchall()
        for sid, context in rows_to_embed:
            if not context:
                continue
            vec = embedder.embed_documents([context])[0]
            cur.execute(
                "INSERT INTO vec_solutions(solution_id, embedding) VALUES (%s, %s) ON CONFLICT (solution_id) DO UPDATE SET embedding = EXCLUDED.embedding;",
                (sid, vec)
            )
        
        # --- Projects ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vec_projects (
                project_id INTEGER PRIMARY KEY,
                embedding vector(1536)
            );
        """)
        
        cur.execute("SELECT project_id, description FROM projects;")
        rows_to_embed = cur.fetchall()
        for pid, desc in rows_to_embed:
            if not desc:
                continue
            vec = embedder.embed_documents([desc])[0]
            cur.execute(
                "INSERT INTO vec_projects(project_id, embedding) VALUES (%s, %s) ON CONFLICT (project_id) DO UPDATE SET embedding = EXCLUDED.embedding;",
                (pid, vec)
            )

        # --- Problems ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vec_problems (
                problem_id INTEGER PRIMARY KEY,
                embedding vector(1536)
            );
        """)

        cur.execute("SELECT problem_id, context FROM problems;")
        rows_to_embed = cur.fetchall()
        for pid, context in rows_to_embed:
            if not context:
                continue
            vec = embedder.embed_documents([context])[0]
            cur.execute(
                "INSERT INTO vec_problems(problem_id, embedding) VALUES (%s, %s) ON CONFLICT (problem_id) DO UPDATE SET embedding = EXCLUDED.embedding;",
                (pid, vec)
            )
            
            db.conn.commit()
            print("Vector embeddings rebuilt successfully.")

if __name__ == "__main__":
    main()