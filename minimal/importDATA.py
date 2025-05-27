import pandas as pd
import sqlite3

# Load CSV
df = pd.read_csv('premier-player-23-24.csv')

# Connect to SQLite DB (or create if not exists)
conn = sqlite3.connect('yourdata.db')

# Write to a table (replace 'my_table' with your table name)
df.to_sql('my_table', conn, if_exists='replace', index=False)
conn.close()
