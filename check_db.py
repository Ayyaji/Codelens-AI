import sqlite3
conn = sqlite3.connect('codelens.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM sessions LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(row)