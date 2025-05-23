import typer
from src.problem_detector   import detect_problems
from src.embed_and_match    import match_embeddings
from src.output_generator   import generate_output

app = typer.Typer()

@app.command()
def detect(
    db_file: str = "donation.db",
    message_file: str = "message.txt"
):
    ids = detect_problems(db_file, message_file)
    typer.echo(f"🔍 Detected problem IDs: {ids}")

@app.command()
def match(
    db_file: str = "donation.db",
    k: int     = 10
):
    sol_ids, proj_ids = match_embeddings(db_file, k=k)
    typer.echo(f"🤝 Matched solution IDs: {sol_ids}")
    typer.echo(f"🏷  Matched project IDs:  {proj_ids}")

@app.command()
def output(
    db_file:    str = "donation.db",
    message_file:str = "message.txt",
    top_n:      int = 5
):
    # You could pull project_ids from a previous run, but here we chain.
    typer.echo("💬 Generating final reply…")
    reply = generate_output(db_file, message_file, top_n=top_n)
    typer.echo(reply)

@app.command()
def run(
    db_file:     str = "donation.db",
    message_file:str = "message.txt",
    k:           int = 10,
    top_n:       int = 5
):
    # Full one-click pipeline
    p_ids       = detect_problems(db_file, message_file)
    sol_ids, pr_ids = match_embeddings(db_file, k=k)
    reply       = generate_output(db_file, message_file, pr_ids, top_n=top_n)
    typer.echo(reply)

if __name__ == "__main__":
    app()