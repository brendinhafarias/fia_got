"""
Migracao: adiciona coluna imagem_filename na tabela programas
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'database.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(programas)")
colunas = [row[1] for row in cursor.fetchall()]

if 'imagem_filename' not in colunas:
    cursor.execute("ALTER TABLE programas ADD COLUMN imagem_filename VARCHAR(255)")
    conn.commit()
    print("OK: Coluna imagem_filename adicionada com sucesso.")
else:
    print("OK: Coluna imagem_filename ja existe.")

conn.close()
