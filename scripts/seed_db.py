import os
import json
import psycopg2
from psycopg2.extras import execute_values

# Get DB connection details from environment variables
DB_NAME = os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
DB_HOST = os.environ.get("POSTGRES_HOST")
DB_PORT = os.environ.get("POSTGRES_PORT")

# Path to the initial data directory
DATA_DIR = "initial_data/"

def get_column_type(column_name, value):
    """Infers column type from column name and a sample value."""
    if column_name.endswith("_embedding"):
        if isinstance(value, list):
            return "vector"
    if column_name.endswith("_id") or column_name == "id":
        return "INTEGER"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, float):
        return "REAL"
    if isinstance(value, bool):
        return "BOOLEAN"
    return "TEXT"


def create_table_from_json(cursor, table_name, data):
    """Creates a table based on JSON data."""
    if not data:
        print(f"No data found for table {table_name}, skipping table creation.")
        return

    print(f"Dropping table {table_name} if it exists...")
    cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")

    first_item = data[0]
    columns_with_types = []

    column_names_for_insert = list(first_item.keys())

    pk_col = None
    # Heuristic to find primary key
    singular_name = table_name.rstrip('s')
    if f"{singular_name}_id" in first_item:
        pk_col = f"{singular_name}_id"
    elif 'id' in first_item:
        pk_col = 'id'

    if pk_col and pk_col in first_item:
        for key, value in first_item.items():
            col_type = get_column_type(key, value)
            if key == pk_col:
                columns_with_types.append(f'"{key}" {col_type} PRIMARY KEY')
            else:
                columns_with_types.append(f'"{key}" {col_type}')
    else:
        # Fallback to original logic
        columns_with_types.append("id SERIAL PRIMARY KEY")
        column_names_for_insert = [c for c in column_names_for_insert if c != 'id']
        for key in column_names_for_insert:
            value = first_item.get(key)
            col_type = get_column_type(key, value)
            columns_with_types.append(f'"{key}" {col_type}')

    create_table_sql = f"CREATE TABLE {table_name} ({', '.join(columns_with_types)});"
    print(f"Creating table {table_name}...")
    cursor.execute(create_table_sql)

    return column_names_for_insert


def insert_data(cursor, table_name, columns, data):
    """Inserts data into the specified table."""
    if not data:
        print(f"No data to insert for table {table_name}.")
        return

    # Prepare data for insertion
    # Using .get() provides safety against missing keys in some records
    values = [[row.get(col) for col in columns] for row in data]

    print(f"Inserting {len(values)} records into {table_name}...")

    # Use execute_values for efficient bulk insertion
    columns_formatted = ', '.join(f'"{col}"' for col in columns)
    insert_sql = f"INSERT INTO {table_name} ({columns_formatted}) VALUES %s"
    execute_values(cursor, insert_sql, values)


def main():
    """Main function to seed the database."""
    conn = None
    try:
        print("Connecting to the PostgreSQL database...")
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        print("Ensuring pgvector extension is enabled...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        json_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]

        for filename in sorted(json_files):
            table_name = os.path.splitext(filename)[0]
            file_path = os.path.join(DATA_DIR, filename)

            print(f"\nProcessing {filename} -> table '{table_name}'")

            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON from {filename}. Skipping.")
                    continue

            if not data:
                print(f"File {filename} is empty. Skipping.")
                continue

            columns = create_table_from_json(cursor, table_name, data)
            if columns:
                insert_data(cursor, table_name, columns, data)

        conn.commit()
        print("\nDatabase seeding completed successfully.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    if not all([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT]):
        print("Error: Database connection environment variables are not set.")
        print("Please set DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, and DB_PORT.")
    else:
        main()