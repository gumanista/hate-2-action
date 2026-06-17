#!/usr/bin/env python3
"""
init_db.py — Run once to set up the database.

Usage:
  python init_db.py           # create tables + seed data only
  python init_db.py --embed   # also generate embeddings and similarity tables
"""
import os
import re
import sys
import argparse
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from db.config import DEFAULT_DATABASE_URL, get_database_url

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
DATABASE_URL = get_database_url(DEFAULT_DATABASE_URL)


def run_sql_file(conn, path: str):
    with open(path, "r") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"  ✓ Executed {path}")


_SEED_TABLES = ("organizations", "projects", "problems", "solutions")


def parse_seed_ids(path: str) -> dict:
    """Return {table: [ids]} for the rows defined in the seed SQL file.

    Scans each `INSERT INTO public.<table> ... VALUES (...)` statement and records
    the leading integer (the id column) of every top-level tuple. The scan tracks
    single-quote string state (with '' escaping) and paren depth so parentheses and
    semicolons inside text values do not confuse it.
    """
    with open(path, "r") as f:
        sql = f.read()

    seed_ids = {}
    for table in _SEED_TABLES:
        m = re.search(
            r"INSERT\s+INTO\s+public\." + re.escape(table) + r"\b[^;]*?VALUES",
            sql, re.IGNORECASE | re.DOTALL,
        )
        if not m:
            seed_ids[table] = []
            continue

        ids = []
        depth = 0
        in_str = False
        i = m.end()
        n = len(sql)
        while i < n:
            ch = sql[i]
            if in_str:
                if ch == "'":
                    if i + 1 < n and sql[i + 1] == "'":  # escaped quote
                        i += 2
                        continue
                    in_str = False
            elif ch == "'":
                in_str = True
            elif ch == "(":
                depth += 1
                if depth == 1:  # start of a top-level value tuple
                    j = i + 1
                    while j < n and sql[j] in " \n\t\r":
                        j += 1
                    k = j
                    while k < n and sql[k].isdigit():
                        k += 1
                    if k > j:
                        ids.append(int(sql[j:k]))
            elif ch == ")":
                depth -= 1
            elif ch == ";" and depth == 0:
                break
            i += 1
        seed_ids[table] = ids

    return seed_ids


def wipe_runtime_data(conn, seed_ids: dict):
    """Delete rows that are not part of the seed set (runtime-accumulated data).

    Seed rows and their existing embeddings are preserved. Deletes in FK-safe order:
    link tables -> vec tables -> base tables.
    """
    cur = conn.cursor()

    def delete_non_seed(table, id_col, table_key):
        ids = seed_ids.get(table_key) or []
        if ids:
            cur.execute(
                f"DELETE FROM public.{table} WHERE {id_col} <> ALL(%s)", (ids,)
            )
        else:  # no seed ids parsed for this entity -> nothing is "seed", wipe all
            cur.execute(f"DELETE FROM public.{table}")
        return cur.rowcount

    # Link tables (delete rows referencing any non-seed problem/solution/project/org).
    cur.execute(
        "DELETE FROM public.problems_solutions WHERE problem_id <> ALL(%s) OR solution_id <> ALL(%s)",
        (seed_ids.get("problems") or [], seed_ids.get("solutions") or []),
    )
    cur.execute(
        "DELETE FROM public.projects_solutions WHERE project_id <> ALL(%s) OR solution_id <> ALL(%s)",
        (seed_ids.get("projects") or [], seed_ids.get("solutions") or []),
    )
    cur.execute(
        "DELETE FROM public.organizations_solutions WHERE organization_id <> ALL(%s) OR solution_id <> ALL(%s)",
        (seed_ids.get("organizations") or [], seed_ids.get("solutions") or []),
    )

    # Vec tables.
    delete_non_seed("problems_vec", "problem_id", "problems")
    delete_non_seed("solutions_vec", "solution_id", "solutions")
    delete_non_seed("projects_vec", "project_id", "projects")
    delete_non_seed("organizations_vec", "organization_id", "organizations")

    # Base tables.
    deleted = {
        "problems": delete_non_seed("problems", "problem_id", "problems"),
        "solutions": delete_non_seed("solutions", "solution_id", "solutions"),
        "projects": delete_non_seed("projects", "project_id", "projects"),
        "organizations": delete_non_seed("organizations", "organization_id", "organizations"),
    }

    conn.commit()
    cur.close()
    summary = ", ".join(f"{k}={v}" for k, v in deleted.items())
    print(f"  ✓ Removed runtime (non-seed) rows: {summary}")


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
            except Exception as e:
                print(f"  ⚠️  Failed to insert link in {link_table} ({src_id}={sid}): {e}")
    conn.commit()
    cur.close()
    print(f"  ✓ Computed {inserted} similarity links in {link_table}")


def run_embeddings(conn):
    from utils.llm import get_embedding

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("  Embedding organizations...")
    cur.execute(
        """SELECT o.organization_id, o.name, o.description
           FROM public.organizations o
           WHERE NOT EXISTS (
               SELECT 1 FROM public.organizations_vec v
               WHERE v.organization_id = o.organization_id AND v.embedding IS NOT NULL
           )"""
    )
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
    cur.execute(
        """SELECT p.project_id, p.name, p.description
           FROM public.projects p
           WHERE NOT EXISTS (
               SELECT 1 FROM public.projects_vec v
               WHERE v.project_id = p.project_id AND v.embedding IS NOT NULL
           )"""
    )
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
    cur.execute(
        """SELECT p.problem_id, p.name, p.context, p.content
           FROM public.problems p
           WHERE NOT EXISTS (
               SELECT 1 FROM public.problems_vec v
               WHERE v.problem_id = p.problem_id AND v.embedding IS NOT NULL
           )"""
    )
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
    cur.execute(
        """SELECT s.solution_id, s.name, s.context, s.content
           FROM public.solutions s
           WHERE NOT EXISTS (
               SELECT 1 FROM public.solutions_vec v
               WHERE v.solution_id = s.solution_id AND v.embedding IS NOT NULL
           )"""
    )
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
    parser.add_argument(
        "--keep-runtime", action="store_true",
        help="Keep runtime-accumulated rows (skip wiping non-seed problems/solutions)",
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

    if args.keep_runtime:
        print("\n   Skipping runtime wipe (--keep-runtime).")
    else:
        print("\n   Resetting to seed-only data...")
        wipe_runtime_data(conn, parse_seed_ids("db/seed.sql"))

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
