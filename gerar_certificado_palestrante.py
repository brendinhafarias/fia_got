#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para gerar certificados para PALESTRANTES
Uso: python gerar_certificado_palestrante.py "Nome Palestrante" palestra1
"""

from app import app, PALESTRAS_IMERSAO
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
import sys
import os

def gerar_certificado_palestrante(nome_palestrante, palestra_id):
    with app.app_context():
        if palestra_id not in PALESTRAS_IMERSAO:
            print(f"❌ Palestra '{palestra_id}' não existe!")
            print(f"Palestras disponíveis: {list(PALESTRAS_IMERSAO.keys())}")
            return False
        
        palestra = PALESTRAS_IMERSAO[palestra_id]
        
        buffer = BytesIO()
        largura, altura = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))
        
        # Cores
        cor_primaria = colors.HexColor("#da6b2d")
        cor_secundaria = colors.HexColor("#1a1a1a")
        cor_texto = colors.HexColor("#333333")
        cor_cinza = colors.HexColor("#6c757d")
        
        # Template/Borda
        BASEDIR = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(BASEDIR, 'static', 'certificado_template.png')
        
        if os.path.exists(template_path):
            c.drawImage(template_path, 0, 0, width=largura, height=altura, preserveAspectRatio=True)
        else:
            c.setStrokeColor(cor_primaria)
            c.setLineWidth(4)
            c.rect(30, 30, largura-60, altura-60, stroke=1, fill=0)
            c.setLineWidth(1)
            c.rect(40, 40, largura-80, altura-80, stroke=1, fill=0)
        
        yposition = altura - 160
        
        # Certificamos que
        c.setFillColor(cor_texto)
        c.setFont("Helvetica", 13)
        c.drawCentredString(largura/2, yposition, "Certificamos que")
        yposition -= 35
        
        # NOME PALESTRANTE
        c.setFillColor(cor_primaria)
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(largura/2, yposition, nome_palestrante.upper())
        yposition -= 35
        
        # Ministrou
        c.setFillColor(cor_texto)
        c.setFont("Helvetica", 12)
        c.drawCentredString(largura/2, yposition, "ministrou a atividade")
        yposition -= 22
        
        # TÍTULO PALESTRA
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(cor_secundaria)
        titulo_palestra = palestra['titulo']
        maxwidth = largura - 150
        
        if c.stringWidth(titulo_palestra, 'Helvetica-Bold', 14) > maxwidth:
            palavras = titulo_palestra.split()
            meio = len(palavras) // 2
            linha1 = ' '.join(palavras[:meio])
            linha2 = ' '.join(palavras[meio:])
            c.drawCentredString(largura/2, yposition, linha1)
            yposition -= 18
            c.drawCentredString(largura/2, yposition, linha2)
            yposition -= 22
        else:
            c.drawCentredString(largura/2, yposition, titulo_palestra)
            yposition -= 22
        
        # Data + Imersão
        c.setFont("Helvetica", 12)
        c.setFillColor(cor_texto)
        data_palestra = palestra['data']
        c.drawCentredString(largura/2, yposition, f"realizada em {data_palestra}, durante a")
        yposition -= 18
        
        c.drawCentredString(largura/2, yposition, "IMERSÃO MULHERES NO MOTORSPORT 2026.")
        yposition -= 22
        
        # AGRADECIMENTO (NOVO)
        c.setFont("Helvetica-Oblique", 11)
        c.setFillColor(cor_cinza)
        c.drawCentredString(largura/2, yposition, "A CFA e a CBA agradecem a sua participação na")
        yposition -= 16
        c.drawCentredString(largura/2, yposition, "Imersão para Mulheres no Motorsport 2026.")
        yposition -= 30
        
        # INGLÊS
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(cor_cinza)
        c.drawCentredString(largura/2, yposition, f"We certify that {nome_palestrante} successfully taught the activity")
        yposition -= 14
        
        # Título inglês
        c.setFont("Helvetica-BoldOblique", 10)
        if c.stringWidth(titulo_palestra, 'Helvetica-BoldOblique', 10) > maxwidth:
            palavras = titulo_palestra.split()
            meio = len(palavras) // 2
            linha1 = ' '.join(palavras[:meio])
            linha2 = ' '.join(palavras[meio:])
            c.drawCentredString(largura/2, yposition, linha1)
            yposition -= 12
            c.drawCentredString(largura/2, yposition, linha2)
            yposition -= 14
        else:
            c.drawCentredString(largura/2, yposition, titulo_palestra)
            yposition -= 14
        
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(largura/2, yposition, f"carried out on {data_palestra}, during the")
        yposition -= 12
        c.drawCentredString(largura/2, yposition, "IMERSÃO MULHERES NO MOTORSPORT 2026.")
        
        # Data emissão
        c.setFont("Helvetica", 9)
        c.setFillColor(cor_cinza)
        data_emissao = datetime.now().strftime("%d de %B de %Y")
        meses = {
            'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
            'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
            'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
            'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
        }
        for en, pt in meses.items():
            data_emissao = data_emissao.replace(en, pt)
        c.drawCentredString(largura/2, 60, f"Emitido em {data_emissao}")
        
        c.showPage()
        c.save()
        buffer.seek(0)
        
        # Salvar
        filename = f"Certificado_Palestrante_{nome_palestrante.replace(' ', '_')}_Palestra{palestra['numero']}.pdf"
        with open(filename, 'wb') as f:
            f.write(buffer.getvalue())
        
        print(f"✅ Certificado de PALESTRANTE gerado!")
        print(f"   Nome: {nome_palestrante}")
        print(f"   Palestra: {palestra['numero']} - {palestra['titulo']}")
        print(f"   Arquivo: {filename}")
        return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("❌ Uso: python gerar_certificado_palestrante.py \"Nome\" palestra1")
        print("\nExemplo: python gerar_certificado_palestrante.py \"Bia Figueiredo\" palestra1")
        sys.exit(1)
    
    nome = sys.argv[1]
    palestra_id = sys.argv[2]
    
    sucesso = gerar_certificado_palestrante(nome, palestra_id)
    sys.exit(0 if sucesso else 1)


