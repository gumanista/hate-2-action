#!/usr/bin/env python3
"""Convert test.json into a JSONL SFT dataset for a Gemma chat/instruct model.

The fine-tuning task is ONLY final reply generation for the Hate-2-Action
Telegram bot: given a user complaint/frustration (plus language/style/topic
hints), produce a short, practical, safe assistant reply.

Output is a columnar JSONL dataset: every line is a flat object whose keys are
dataset columns. The fine-tuning platform maps columns to chat roles --
  system      -> System
  instruction -> User
  response    -> Assistant
-- and treats the rest (lang, style, topic, source_id, ...) as metadata.

Standard library only. Does not modify the input file.
"""

import argparse
import json
import os
import random
import sys
from collections import Counter

SYSTEM_PROMPT = (
    "You are Hate-2-Action Bot. Reply in the requested language. Transform user "
    "frustration into concrete action. Keep replies short. Follow the requested "
    "style. Do not assume the user's emotional state. Do not invent facts, "
    "locations, organizations, or links. If mentioning organizations or projects, "
    "use only information already present in the provided context or target style."
)

USER_TEMPLATE = (
    "Language: {lang}\n"
    "Style: {style}\n"
    "Topic: {topic}\n\n"
    "User message:\n"
    "{message_input}"
)


def clean(value):
    """Return a stripped string for any field, tolerating None/missing/non-str."""
    if value is None:
        return ""
    return str(value).strip()


def build_example(row):
    """Build one SFT example from a row, or return None if the row is invalid.

    Returns a tuple (example_dict, used_new_output) on success.
    """
    message_input = clean(row.get("message_input"))
    if not message_input:
        return None  # rule 5: skip rows without a user message

    new_output = clean(row.get("new_output"))
    output = clean(row.get("output"))

    # rules 2-4: prefer non-empty new_output, else output; never the model fields
    if new_output:
        chosen_output = new_output
        used_new_output = True
    else:
        chosen_output = output
        used_new_output = False

    if not chosen_output:
        return None  # rule 6: skip rows without a usable assistant target

    lang = clean(row.get("lang"))
    style = clean(row.get("style"))
    topic = clean(row.get("topic"))
    comment = clean(row.get("comment"))

    user_content = USER_TEMPLATE.format(
        lang=lang,
        style=style,
        topic=topic,
        message_input=message_input,
    )

    # source_id: keep the original id as-is when present (don't invent one)
    source_id = row.get("id")

    # Flat, columnar record: each key is a dataset column. The fine-tuning
    # platform maps columns to chat roles (system -> System, instruction ->
    # User, response -> Assistant); the remaining columns are metadata.
    example = {
        "system": SYSTEM_PROMPT,
        "instruction": user_content,
        "response": chosen_output,
        "lang": lang,
        "style": style,
        "topic": topic,
        "source_id": source_id,
        "used_new_output": used_new_output,
        "has_comment": bool(comment),
    }
    return example, used_new_output


# Columns that must be present and non-empty on every written record. These
# are the three the platform maps to chat roles.
REQUIRED_COLUMNS = ("system", "instruction", "response")


def is_valid_example(example):
    """Validate the columnar contract before a record is written to disk."""
    if not isinstance(example, dict):
        return False

    for column in REQUIRED_COLUMNS:
        value = example.get(column)
        if not isinstance(value, str) or not value.strip():
            return False

    # Final guard: the record must be JSON-serializable.
    try:
        json.dumps(example, ensure_ascii=False)
    except (TypeError, ValueError):
        return False
    return True


def write_jsonl(path, examples):
    with open(path, "w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False))
            f.write("\n")


def split_dataset(examples, train_ratio, val_ratio):
    """Split into (train, val, test). test gets the remainder."""
    n = len(examples)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    # Guard against rounding pushing train+val past n.
    if n_train + n_val > n:
        n_val = max(0, n - n_train)
    train = examples[:n_train]
    val = examples[n_train:n_train + n_val]
    test = examples[n_train + n_val:]
    return train, val, test


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Build a JSONL SFT dataset from test.json for Gemma fine-tuning."
    )
    parser.add_argument("--input", default="test.json",
                        help="Path to the input JSON array (default: test.json).")
    parser.add_argument("--output-dir", default="data/finetune",
                        help="Directory for the JSONL splits (default: data/finetune).")
    parser.add_argument("--train-ratio", type=float, default=0.9,
                        help="Fraction of examples for train (default: 0.9).")
    parser.add_argument("--val-ratio", type=float, default=0.05,
                        help="Fraction of examples for val (default: 0.05).")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for deterministic shuffling (default: 42).")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.train_ratio < 0 or args.val_ratio < 0:
        print("Error: ratios must be non-negative.", file=sys.stderr)
        return 1
    if args.train_ratio + args.val_ratio > 1.0:
        print("Error: train-ratio + val-ratio must not exceed 1.0.", file=sys.stderr)
        return 1

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Error: could not parse JSON from {args.input}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(data, list):
        print("Error: input must be a JSON array.", file=sys.stderr)
        return 1

    total_input = len(data)
    examples = []
    skipped = 0
    used_new_output_count = 0
    lang_counts = Counter()
    style_counts = Counter()
    topic_counts = Counter()

    for row in data:
        if not isinstance(row, dict):
            skipped += 1
            continue
        built = build_example(row)
        if built is None:
            skipped += 1
            continue
        example, used_new_output = built
        if not is_valid_example(example):
            skipped += 1
            continue

        examples.append(example)
        if used_new_output:
            used_new_output_count += 1
        lang_counts[example["lang"] or "(empty)"] += 1
        style_counts[example["style"] or "(empty)"] += 1
        topic_counts[example["topic"] or "(empty)"] += 1

    # Deterministic shuffle, then split.
    rng = random.Random(args.seed)
    rng.shuffle(examples)
    train, val, test = split_dataset(examples, args.train_ratio, args.val_ratio)

    os.makedirs(args.output_dir, exist_ok=True)
    full_path = os.path.join(args.output_dir, "full.jsonl")
    train_path = os.path.join(args.output_dir, "train.jsonl")
    val_path = os.path.join(args.output_dir, "val.jsonl")
    test_path = os.path.join(args.output_dir, "test.jsonl")
    stats_path = os.path.join(args.output_dir, "dataset_stats.json")

    # full.jsonl holds every valid example (shuffled order == train+val+test).
    write_jsonl(full_path, examples)
    write_jsonl(train_path, train)
    write_jsonl(val_path, val)
    write_jsonl(test_path, test)

    stats = {
        "input_file": args.input,
        "total_input_rows": total_input,
        "written_examples": len(examples),
        "skipped_rows": skipped,
        "used_new_output": used_new_output_count,
        "splits": {
            "full": len(examples),
            "train": len(train),
            "val": len(val),
            "test": len(test),
        },
        "ratios": {
            "train_ratio": args.train_ratio,
            "val_ratio": args.val_ratio,
            "test_ratio": round(1.0 - args.train_ratio - args.val_ratio, 6),
        },
        "seed": args.seed,
        "columns": [
            "system", "instruction", "response",
            "lang", "style", "topic",
            "source_id", "used_new_output", "has_comment",
        ],
        "role_mapping": {
            "system": "System",
            "instruction": "User",
            "response": "Assistant",
        },
        "counts_by_lang": dict(sorted(lang_counts.items())),
        "counts_by_style": dict(sorted(style_counts.items())),
        "counts_by_topic": dict(sorted(topic_counts.items())),
    }
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Concise summary to stdout.
    print("Hate-2-Action fine-tuning dataset build")
    print("=" * 40)
    print(f"Input file          : {args.input}")
    print(f"Total input rows    : {total_input}")
    print(f"Written examples    : {len(examples)}")
    print(f"Skipped rows        : {skipped}")
    print(f"Using new_output    : {used_new_output_count}")
    print(f"Full dataset        : {len(examples)}")
    print(f"Splits              : train={len(train)} val={len(val)} test={len(test)}")
    print(f"Output directory    : {args.output_dir}")
    print("Column -> role map  : system->System  instruction->User  response->Assistant")

    def print_counts(title, counter):
        print(f"\n{title}:")
        for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {key}: {count}")

    print_counts("Counts by language", lang_counts)
    print_counts("Counts by style", style_counts)
    print_counts("Counts by topic", topic_counts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
