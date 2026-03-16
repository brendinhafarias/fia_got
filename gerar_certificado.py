#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para gerar certificados por email e palestra específica
Uso: python gerar_certificado.py email@exemplo.com palestra1
"""

from app import app, db, PALESTRAS_IMERSAO, gerar_pdf_certificado_palestra
import sys

def gerar_certificado_email(email, palestra_id):
    with app.app_context():
        # Buscar inscrição
        result = db.session.execute(db.text("""
            SELECT id, nome, email
            FROM inscricoes 
            WHERE LOWER(email) = LOWER(:email)
            AND programa_id = (SELECT id FROM programas WHERE slug = 'imersao')
        """), {'email': email}).fetchone()
        
        if not result:
            print(f"❌ Email '{email}' não encontrado no programa Imersão.")
            return False
        
        inscricao_id, nome, email_real = result
        
        # Verificar se palestra existe
        if palestra_id not in PALESTRAS_IMERSAO:
            print(f"❌ Palestra '{palestra_id}' não existe!")
            print(f"Palestras disponíveis: {list(PALESTRAS_IMERSAO.keys())}")
            return False
        
        # Buscar objeto completo
        from app import Inscricao
        inscricao = Inscricao.query.get(inscricao_id)
        
        # Gerar PDF
        palestra = PALESTRAS_IMERSAO[palestra_id]
        buffer = gerar_pdf_certificado_palestra(inscricao, palestra_id)
        
        if buffer:
            filename = f"Certificado_{nome.replace(' ', '_')}_Palestra{palestra['numero']}.pdf"
            
            # Salvar local
            with open(filename, 'wb') as f:
                f.write(buffer.getvalue())
            
            print(f"✅ Certificado gerado com sucesso!")
            print(f"   Nome: {nome}")
            print(f"   Email: {email_real}")
            print(f"   Palestra: {palestra['numero']} - {palestra['titulo']}")
            print(f"   Arquivo: {filename}")
            return True
        else:
            print(f"❌ Erro ao gerar PDF!")
            return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("❌ Uso: python gerar_certificado.py email@exemplo.com palestra1")
        print("\nExemplo: python gerar_certificado.py mihuniversidade@gmail.com palestra1")
        print("\nPalestras disponíveis:")
        for pid, pdata in PALESTRAS_IMERSAO.items():
            print(f"  - {pid}: Palestra {pdata['numero']} - {pdata['titulo']}")
        sys.exit(1)
    
    email = sys.argv[1]
    palestra_id = sys.argv[2]
    
    sucesso = gerar_certificado_email(email, palestra_id)
    sys.exit(0 if sucesso else 1)
