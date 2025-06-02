#!/usr/bin/env python3
import os
import sqlite3
import sys
import argparse

from src.pipeline import process_message
from src.telegram.config import Config

DB_PATH = getattr(Config, "DB_PATH",
                  os.getenv("DB_PATH", "donation.db"))

def cmd_run_id(args):
    reply = process_message(args.message_id, db_file=DB_PATH)
    print(reply)

def cmd_run(args):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO messages (user_id, user_username, chat_title, text) VALUES (?, ?, ?, ?)",
        (args.user_id, args.username, args.chat_title, args.text)
    )
    message_id = cur.lastrowid
    conn.commit()
    conn.close()

    reply = process_message(message_id, db_file=DB_PATH)
    print(reply)
    

def main():
    parser = argparse.ArgumentParser(prog="cli.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p1 = subparsers.add_parser("run-id", help="Process an existing message by ID")
    p1.add_argument("message_id", type=int, help="ID of the message in the DB")
    p1.set_defaults(func=cmd_run_id)

    p2 = subparsers.add_parser("run", help="Insert & process a new message")
    p2.add_argument("text",      help="Raw message text to insert & process")
    p2.add_argument("--user-id",   type=int, default=0,   help="User ID to store")
    p2.add_argument("--username",  default="", help="Username to store")
    p2.add_argument("--chat-title",default="", help="Chat title to store")
    p2.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
