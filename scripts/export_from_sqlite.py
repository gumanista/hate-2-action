import sqlite3
import json
import os

class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            try:
                return obj.decode('utf-8')
            except UnicodeDecodeError:
                return obj.hex()
        return super().default(obj)


# Define the paths
DB_PATH = 'donation.db'
OUTPUT_DIR = 'initial_data'


def export_tables_to_json():
    """
    Connects to the SQLite database, inspects it to find all tables,
    and exports each table's data to a corresponding JSON file.
    """
    # Ensure the output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    conn = None
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get a list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        # Process each table
        for table_name_tuple in tables:
            table_name = table_name_tuple[0]

            # Skip sqlite internal and vector tables
            if table_name.startswith('sqlite_') or table_name.startswith('vec_'):
                continue

            print(f"Exporting table: {table_name}...")

            try:
                # Fetch all data from the table
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()

                # Get column names
                column_names = [description[0] for description in cursor.description]

                # Convert rows to a list of dictionaries
                data = [dict(zip(column_names, row)) for row in rows]

                # Define the output file path
                output_file = os.path.join(OUTPUT_DIR, f"{table_name}.json")

                # Write the data to a JSON file
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=4, cls=BytesEncoder)

                print(f"Successfully exported {len(data)} rows to {output_file}")
            except Exception as e:
                print(f"Could not export table '{table_name}': {e}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    export_tables_to_json()