"""
Migração: preenche dados do programa FIA Girls on Track - Experiência WEC 2026
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, Programa

DESCRICAO_CURTA = (
    "Viva de perto a adrenalina das 6 Horas de São Paulo do FIA World Endurance Championship "
    "como parte da equipe de apoio no Autódromo de Interlagos."
)

DESCRICAO = """O FIA Girls on Track – Experiência WEC é uma oportunidade única para mulheres que desejam dar os primeiros passos no mundo do automobilismo profissional.

Selecionadas passarão um fim de semana imerso na etapa brasileira do FIA World Endurance Championship (WEC) — as 6 Horas de São Paulo —, realizada no icônico Autódromo José Carlos Pace (Interlagos), em São Paulo – SP.

Durante o evento, as participantes terão contato direto com equipes, pilotos e profissionais do paddock, vivenciando na prática as diferentes áreas que movem o motorsport de endurance de alto nível: Engenharia, Mecânica, Comunicação, Marketing, Logística, TI e muito mais.

📍 Local: Autódromo José Carlos Pace – Interlagos, São Paulo – SP
🏁 Evento: FIA WEC – 6 Horas de São Paulo 2026

Esta é a sua chance de transformar a paixão pelo automobilismo em experiência real."""

with app.app_context():
    programa = Programa.query.filter_by(slug='experiencia-wec').first()
    if not programa:
        print("ERRO: Programa 'experiencia-wec' nao encontrado. Execute 'flask init-db' primeiro.")
        sys.exit(1)

    programa.nome = 'FIA Girls on Track - Experiência WEC'
    programa.descricao_curta = DESCRICAO_CURTA
    programa.descricao = DESCRICAO
    db.session.commit()
    print("OK: Programa 'FIA Girls on Track - Experiencia WEC' atualizado com sucesso!")
