# src/cli.py

import typer
from src.problem_detector import detect_problems
from src.embed_and_match  import match_embeddings
from src.output_generator import generate_output

app = typer.Typer()

@app.command()
def detect(
    db_file:     str = "donation.db",
    message_file:str = "message.txt"
):
    ids = detect_problems(db_file, message_file)
    typer.echo(f"🔍 Detected problem IDs: {ids}")

@app.command()
def run(
    db_file:     str = "donation.db",
    message_file:str = "message.txt",
    k:           int = 10,
    top_n:       int = 5
):
    # Full one-click pipeline
    p_ids         = detect_problems(db_file, message_file)
    sol_ids, pr_ids = match_embeddings(db_file, p_ids, k=k)
    reply         = generate_output(db_file, message_file, p_ids, pr_ids, top_n=top_n)
    typer.echo(reply)

if __name__ == "__main__":
    app()
