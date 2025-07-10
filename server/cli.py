#!/usr/bin/env python3
import os
import sys
import httpx
import argparse
import json

# --- Environment Variables ---
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY")

def get_client():
    if not API_KEY:
        print("Error: API_KEY environment variable not set.")
        sys.exit(1)
    return httpx.Client(base_url=API_URL, headers={"X-API-Key": API_KEY})

def handle_response(response: httpx.Response):
    if response.status_code >= 400:
        print(f"Error: {response.status_code} - {response.text}")
    else:
        try:
            print(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            if response.text:
                print(response.text)
            else:
                print(f"Status code: {response.status_code}")

# --- Command Functions ---

def cmd_process_message(client: httpx.Client, args):
    """Process a message through the API."""
    print("📨 Processing message...")
    response = client.post("/process-message", json={"message": args.text})
    handle_response(response)

# --- CRUD for Projects ---
def cmd_create_project(client: httpx.Client, args):
    data = {
        "name": args.name,
        "description": args.description,
        "website": args.website,
        "contact_email": args.contact_email,
    }
    response = client.post("/projects", json=data)
    handle_response(response)

def cmd_get_projects(client: httpx.Client, args):
    response = client.get("/projects")
    handle_response(response)

def cmd_get_project(client: httpx.Client, args):
    response = client.get(f"/projects/{args.id}")
    handle_response(response)

def cmd_update_project(client: httpx.Client, args):
    data = {}
    if args.name:
        data["name"] = args.name
    if args.description:
        data["description"] = args.description
    if args.website:
        data["website"] = args.website
    if args.contact_email:
        data["contact_email"] = args.contact_email
    
    if not data:
        print("No fields to update.")
        return

    response = client.put(f"/projects/{args.id}", json=data)
    handle_response(response)

def cmd_delete_project(client: httpx.Client, args):
    response = client.delete(f"/projects/{args.id}")
    handle_response(response)

# --- CRUD for Problems ---
def cmd_create_problem(client: httpx.Client, args):
    data = {"name": args.name, "context": args.context}
    response = client.post("/problems", json=data)
    handle_response(response)

def cmd_get_problems(client: httpx.Client, args):
    response = client.get("/problems")
    handle_response(response)

def cmd_get_problem(client: httpx.Client, args):
    response = client.get(f"/problems/{args.id}")
    handle_response(response)

def cmd_update_problem(client: httpx.Client, args):
    data = {}
    if args.name:
        data["name"] = args.name
    if args.context:
        data["context"] = args.context
    if args.is_processed is not None:
        data["is_processed"] = args.is_processed
    
    if not data:
        print("No fields to update.")
        return
        
    response = client.put(f"/problems/{args.id}", json=data)
    handle_response(response)

def cmd_delete_problem(client: httpx.Client, args):
    response = client.delete(f"/problems/{args.id}")
    handle_response(response)

# --- CRUD for Solutions ---
def cmd_create_solution(client: httpx.Client, args):
    data = {"name": args.name, "context": args.context}
    response = client.post("/solutions", json=data)
    handle_response(response)

def cmd_get_solutions(client: httpx.Client, args):
    response = client.get("/solutions")
    handle_response(response)

def cmd_get_solution(client: httpx.Client, args):
    response = client.get(f"/solutions/{args.id}")
    handle_response(response)

def cmd_update_solution(client: httpx.Client, args):
    data = {}
    if args.name:
        data["name"] = args.name
    if args.context:
        data["context"] = args.context
        
    if not data:
        print("No fields to update.")
        return

    response = client.put(f"/solutions/{args.id}", json=data)
    handle_response(response)

def cmd_delete_solution(client: httpx.Client, args):
    response = client.delete(f"/solutions/{args.id}")
    handle_response(response)


def main():
    parser = argparse.ArgumentParser(prog="cli.py", description="CLI tool to interact with the API.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Process Message ---
    p_process = subparsers.add_parser("process-message", help="Process a new message.")
    p_process.add_argument("text", help="Raw message text to process")
    p_process.set_defaults(func=cmd_process_message)

    # --- Projects ---
    p_projects = subparsers.add_parser("projects", help="Manage projects.")
    sp_projects = p_projects.add_subparsers(dest="action", required=True)
    
    p_create = sp_projects.add_parser("create", help="Create a project.")
    p_create.add_argument("name", help="Name of the project")
    p_create.add_argument("--description", help="Description of the project")
    p_create.add_argument("--website", help="Website of the project")
    p_create.add_argument("--contact-email", help="Contact email for the project")
    p_create.set_defaults(func=cmd_create_project)

    p_list = sp_projects.add_parser("list", help="List all projects.")
    p_list.set_defaults(func=cmd_get_projects)

    p_get = sp_projects.add_parser("get", help="Get a specific project.")
    p_get.add_argument("id", type=int, help="ID of the project")
    p_get.set_defaults(func=cmd_get_project)

    p_update = sp_projects.add_parser("update", help="Update a project.")
    p_update.add_argument("id", type=int, help="ID of the project")
    p_update.add_argument("--name", help="New name for the project")
    p_update.add_argument("--description", help="New description for the project")
    p_update.add_argument("--website", help="New website for the project")
    p_update.add_argument("--contact-email", help="New contact email for the project")
    p_update.set_defaults(func=cmd_update_project)

    p_delete = sp_projects.add_parser("delete", help="Delete a project.")
    p_delete.add_argument("id", type=int, help="ID of the project")
    p_delete.set_defaults(func=cmd_delete_project)

    # --- Problems ---
    p_problems = subparsers.add_parser("problems", help="Manage problems.")
    sp_problems = p_problems.add_subparsers(dest="action", required=True)

    p_create = sp_problems.add_parser("create", help="Create a problem.")
    p_create.add_argument("name", help="Name of the problem")
    p_create.add_argument("--context", help="Context of the problem")
    p_create.set_defaults(func=cmd_create_problem)

    p_list = sp_problems.add_parser("list", help="List all problems.")
    p_list.set_defaults(func=cmd_get_problems)

    p_get = sp_problems.add_parser("get", help="Get a specific problem.")
    p_get.add_argument("id", type=int, help="ID of the problem")
    p_get.set_defaults(func=cmd_get_problem)

    p_update = sp_problems.add_parser("update", help="Update a problem.")
    p_update.add_argument("id", type=int, help="ID of the problem")
    p_update.add_argument("--name", help="New name for the problem")
    p_update.add_argument("--context", help="New context for the problem")
    p_update.add_argument("--is-processed", type=bool, help="Set problem as processed")
    p_update.set_defaults(func=cmd_update_problem)

    p_delete = sp_problems.add_parser("delete", help="Delete a problem.")
    p_delete.add_argument("id", type=int, help="ID of the problem")
    p_delete.set_defaults(func=cmd_delete_problem)

    # --- Solutions ---
    p_solutions = subparsers.add_parser("solutions", help="Manage solutions.")
    sp_solutions = p_solutions.add_subparsers(dest="action", required=True)

    p_create = sp_solutions.add_parser("create", help="Create a solution.")
    p_create.add_argument("name", help="Name of the solution")
    p_create.add_argument("--context", help="Context of the solution")
    p_create.set_defaults(func=cmd_create_solution)

    p_list = sp_solutions.add_parser("list", help="List all solutions.")
    p_list.set_defaults(func=cmd_get_solutions)

    p_get = sp_solutions.add_parser("get", help="Get a specific solution.")
    p_get.add_argument("id", type=int, help="ID of the solution")
    p_get.set_defaults(func=cmd_get_solution)

    p_update = sp_solutions.add_parser("update", help="Update a solution.")
    p_update.add_argument("id", type=int, help="ID of the solution")
    p_update.add_argument("--name", help="New name for the solution")
    p_update.add_argument("--context", help="New context for the solution")
    p_update.set_defaults(func=cmd_update_solution)

    p_delete = sp_solutions.add_parser("delete", help="Delete a solution.")
    p_delete.add_argument("id", type=int, help="ID of the solution")
    p_delete.set_defaults(func=cmd_delete_solution)

    args = parser.parse_args()
    with get_client() as client:
        args.func(client, args)

if __name__ == "__main__":
    main()
