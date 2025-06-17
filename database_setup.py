import sqlite3

# Define the name of our database file.
# It will be created in the same directory as the script.
DATABASE_FILE = "stock_news.db"

def create_database_and_table():
    """
    Connects to the SQLite database (creating it if it doesn't exist)
    and creates the 'articles' table with our desired schema.
    """
    conn = None  # Initialize connection to None
    try:
        # 1. Connect to the database.
        # This command creates the file 'stock_news.db' if it's not already there.
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print("Database created and successfully connected to SQLite.")

        # 2. Define the SQL command to create the 'articles' table.
        # We use triple quotes for a multi-line string.
        sql_create_articles_table = """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            publication_date TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            article_text TEXT,
            attachments_text TEXT,
            processing_status TEXT NOT NULL DEFAULT 'pending',
            llm_evaluation TEXT,
            llm_reasoning TEXT,
            llm_confidence REAL
        );
        """

        # 3. Execute the SQL command.
        cursor.execute(sql_create_articles_table)
        print("Table 'articles' created or already exists.")

        # 4. Commit the changes to the database.
        # This saves the table structure.
        conn.commit()

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        # 5. Close the connection.
        # It's important to close the connection, whether an error occurred or not.
        if conn:
            conn.close()
            print("The SQLite connection is closed.")


if __name__ == "__main__":
    create_database_and_table()