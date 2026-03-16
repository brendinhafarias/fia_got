
# migration_add_observacao_curriculo.py
# Execute este script UMA VEZ para adicionar os novos campos ao banco

from app import app, db, Inscricao

with app.app_context():
    # Adicionar as novas colunas ao banco de dados
    with db.engine.connect() as conn:
        try:
            # Adicionar campo observacao_admin
            conn.execute(db.text("ALTER TABLE inscricoes ADD COLUMN observacao_admin TEXT"))
            print("✓ Campo 'observacao_admin' adicionado")
        except Exception as e:
            print(f"Campo 'observacao_admin' já existe ou erro: {e}")

        try:
            # Adicionar campo curriculo_visto
            conn.execute(db.text("ALTER TABLE inscricoes ADD COLUMN curriculo_visto BOOLEAN DEFAULT 0"))
            print("✓ Campo 'curriculo_visto' adicionado")
        except Exception as e:
            print(f"Campo 'curriculo_visto' já existe ou erro: {e}")

        conn.commit()

    print("\n✓ Migração concluída com sucesso!")
