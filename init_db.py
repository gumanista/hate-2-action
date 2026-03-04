#!/usr/bin/env python3
"""
init_db.py — Run once to set up the database.

Usage:
  python init_db.py           # create tables + seed data only
  python init_db.py --embed   # also generate embeddings and similarity tables
"""

#TODO: ORM frameworks like SQLAlchemy etc
import os
import sys
import argparse
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
DEFAULT_DATABASE_URL = "postgresql://hate2action:hate2action@localhost:5433/hate2action"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def run_sql_file(conn, path: str):
    with open(path, "r") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"  ✓ Executed {path}")


def compute_similarity(conn, src_table, src_id, src_vec_table,
                       tgt_table, tgt_id, tgt_vec_table,
                       link_table, threshold=0.3, top_n=5):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"SELECT {src_id} FROM public.{src_table}")
    src_ids = [r[src_id] for r in cur.fetchall()]

    inserted = 0
    for sid in src_ids:
        cur.execute(
            f"""SELECT t.{tgt_id},
                       1 - (sv.embedding <=> tv.embedding) AS similarity
                FROM public.{src_vec_table} sv
                CROSS JOIN public.{tgt_table} t
                JOIN public.{tgt_vec_table} tv ON t.{tgt_id} = tv.{tgt_id}
                WHERE sv.{src_id} = %s
                  AND sv.embedding IS NOT NULL
                  AND tv.embedding IS NOT NULL
                  AND 1 - (sv.embedding <=> tv.embedding) > %s
                ORDER BY similarity DESC
                LIMIT %s""",
            (sid, threshold, top_n),
        )
        for row in cur.fetchall():
            try:
                cur.execute(
                    f"""INSERT INTO public.{link_table} ({src_id}, {tgt_id}, similarity_score)
                        VALUES (%s, %s, %s)
                        ON CONFLICT ({src_id}, {tgt_id}) DO UPDATE SET similarity_score = EXCLUDED.similarity_score""",
                    (sid, row[tgt_id], row["similarity"]),
                )
                inserted += 1
            except Exception:
                pass
    conn.commit()
    cur.close()
    print(f"  ✓ Computed {inserted} similarity links in {link_table}")


def run_embeddings(conn):
    from utils.llm import get_embedding

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("  Embedding organizations...")
    cur.execute("SELECT organization_id, name, description FROM public.organizations")
    rows = cur.fetchall()
    for row in rows:
        text = f"{row['name']}: {row['description'] or ''}"
        emb = get_embedding(text)
        emb_str = "[" + ",".join(str(v) for v in emb) + "]"
        cur.execute(
            """INSERT INTO public.organizations_vec (organization_id, text_to_embed, embedding)
               VALUES (%s, %s, %s::vector)
               ON CONFLICT (organization_id) DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = now()""",
            (row["organization_id"], text[:2000], emb_str),
        )
    conn.commit()
    print(f"  ✓ Embedded {len(rows)} organizations")

    print("  Embedding projects...")
    cur.execute("SELECT project_id, name, description FROM public.projects")
    rows = cur.fetchall()
    for row in rows:
        text = f"{row['name']}: {row['description'] or ''}"
        emb = get_embedding(text)
        emb_str = "[" + ",".join(str(v) for v in emb) + "]"
        cur.execute(
            """INSERT INTO public.projects_vec (project_id, text_to_embed, embedding)
               VALUES (%s, %s, %s::vector)
               ON CONFLICT (project_id) DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = now()""",
            (row["project_id"], text[:2000], emb_str),
        )
    conn.commit()
    print(f"  ✓ Embedded {len(rows)} projects")

    print("  Embedding problems...")
    cur.execute("SELECT problem_id, name, context, content FROM public.problems")
    rows = cur.fetchall()
    for row in rows:
        text = f"{row['name']}: {row['context'] or ''} {row['content'] or ''}"
        emb = get_embedding(text)
        emb_str = "[" + ",".join(str(v) for v in emb) + "]"
        cur.execute(
            """INSERT INTO public.problems_vec (problem_id, text_to_embed, embedding)
               VALUES (%s, %s, %s::vector)
               ON CONFLICT (problem_id) DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = now()""",
            (row["problem_id"], text[:2000], emb_str),
        )
        cur.execute(
            "UPDATE public.problems SET embedding = %s::vector WHERE problem_id = %s",
            (emb_str, row["problem_id"]),
        )
    conn.commit()
    print(f"  ✓ Embedded {len(rows)} problems")

    print("  Embedding solutions...")
    cur.execute("SELECT solution_id, name, context, content FROM public.solutions")
    rows = cur.fetchall()
    for row in rows:
        text = f"{row['name']}: {row['context'] or ''} {row['content'] or ''}"
        emb = get_embedding(text)
        emb_str = "[" + ",".join(str(v) for v in emb) + "]"
        cur.execute(
            """INSERT INTO public.solutions_vec (solution_id, text_to_embed, embedding)
               VALUES (%s, %s, %s::vector)
               ON CONFLICT (solution_id) DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = now()""",
            (row["solution_id"], text[:2000], emb_str),
        )
        cur.execute(
            "UPDATE public.solutions SET embedding = %s::vector WHERE solution_id = %s",
            (emb_str, row["solution_id"]),
        )
    conn.commit()
    print(f"  ✓ Embedded {len(rows)} solutions")
    cur.close()


def main():
    parser = argparse.ArgumentParser(description="Hate-2-Action DB initializer")
    parser.add_argument(
        "--embed", action="store_true",
        help="Generate embeddings and compute similarity tables (requires OPENAI_API_KEY)",
    )
    args = parser.parse_args()

    print("\n🚀 Hate-2-Action DB Initialization\n")
    try:
        conn = psycopg2.connect(DATABASE_URL)
    except psycopg2.OperationalError as exc:
        print("❌ Could not connect to PostgreSQL.")
        print(f"   DATABASE_URL: {DATABASE_URL}")
        print("   If using docker-compose, start DB first: docker-compose up -d db")
        print(f"   Host default for this project is: {DEFAULT_DATABASE_URL}\n")
        raise SystemExit(1) from exc

    print("1. Running schema migrations...")
    run_sql_file(conn, "db/schema.sql")

    print("\n2. Seeding initial data...")
    run_sql_file(conn, "db/seed.sql")

    if not args.embed:
        conn.close()
        print("\n✅ Schema and seed complete.")
        print("   Run with --embed to generate embeddings and similarity tables.\n")
        return

    print("\n3. Generating embeddings...")
    run_embeddings(conn)

    print("\n4. Computing similarity tables...")
    compute_similarity(
        conn,
        "problems", "problem_id", "problems_vec",
        "solutions", "solution_id", "solutions_vec",
        "problems_solutions", threshold=0.3, top_n=5,
    )
    compute_similarity(
        conn,
        "solutions", "solution_id", "solutions_vec",
        "projects", "project_id", "projects_vec",
        "projects_solutions", threshold=0.3, top_n=5,
    )
    compute_similarity(
        conn,
        "solutions", "solution_id", "solutions_vec",
        "organizations", "organization_id", "organizations_vec",
        "organizations_solutions", threshold=0.3, top_n=5,
    )

    conn.close()
    print("\n✅ Database fully initialized!\n")
    print("Next: Run `python bot/main.py` to start the bot.")


if __name__ == "__main__":
    main()
