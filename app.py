import os
import re
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_file, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from email.message import EmailMessage
import smtplib
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from dotenv import load_dotenv
from sqlalchemy.orm.attributes import flag_modified


load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

db = SQLAlchemy(app)

#app.config['PREFERRED_URL_SCHEME'] = 'https'

# ==================== DADOS DAS PALESTRAS ====================
PALESTRAS_IMERSAO = {
    'palestra1': {
        'numero': 1,
        'titulo': 'Apresentação CFA + Spoilers dos projetos que acontecerão em 2026',
        'palestrantes': ['Bia Figueiredo - Presidente da Comissão Feminina de Automobilismo', 'Rachel Loh - Membro da Comissão Feminina de Automobilismo e Engenheira da equipe AMattheis'],
        'data': '02/02/2026',
        'horario': '19h',
        'carga_horaria': '2 horas',
        'link_zoom': 'https://us06web.zoom.us/j/83308080218?pwd=nLx9qZcIOrcA6drtBrYSGbPibXy7iH.1'
    },
    'palestra2': {
        'numero': 2,
        'titulo': 'Marketing Digital e Estratégia no Automobilismo',
        'palestrantes': ['Alice Alves - Social Media da Stock Car'],
        'data': '04/02/2026',
        'horario': '19h',
        'carga_horaria': '2 horas',
        'link_zoom': 'https://us06web.zoom.us/j/85417106701?pwd=jRe4busI4HevEWCabRKM9AHt5bbI8g.1'
    },
    'palestra3': {
        'numero': 3,
        'titulo': 'Direção de Prova no Motorsport',
        'palestrantes': ['Andrea Ladeira - Diretoria de Prova - CBA', 'Gabriela Pedron - Diretoria de Prova - CBA'],
        'data': '05/02/2026',
        'horario': '19h',
        'carga_horaria': '2 horas',
        'link_zoom': 'https://us06web.zoom.us/j/83736904592?pwd=qcnxckpmbAcOFy4HbfEgWzjyMWSNtg.1'
    },
    'palestra4': {
        'numero': 4,
        'titulo': 'Aquisição de Dados no Motorsport',
        'palestrantes': ['Felipe Faria - Engenheiro da Amattheis Vogel'],
        'data': '09/02/2026',
        'horario': '19h',
        'carga_horaria': '2 horas',
        'link_zoom': 'https://us06web.zoom.us/j/85345943439?pwd=pgRHbK7XJYPW2h2n6cIWvvka5N7vDF.1'
    },
    'palestra5': {
        'numero': 5,
        'titulo': 'Construção de Currículo e Carreira no Automobilismo',
        'palestrantes': ['Amanda Rodrigues - Gerente de RH da Porsche Cup Brasil'],
        'data': '11/02/2026',
        'horario': '19h',
        'carga_horaria': '2 horas',
        'link_zoom': 'https://us06web.zoom.us/j/87325836211?pwd=H2XySiijvHx1YJrsYss898E64pqKzf.1'
    }
}



@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# ==================== MODELOS ====================
class AdminUser(db.Model):
    __tablename__ = 'admin_user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class Programa(db.Model):
    __tablename__ = 'programas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    descricao_curta = db.Column(db.String(250), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    data_abertura = db.Column(db.Date, nullable=True)
    data_fechamento = db.Column(db.Date, nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    avisos = db.relationship('Aviso', backref='programa', lazy=True)
    inscricoes = db.relationship('Inscricao', backref='programa', lazy=True)

class Aviso(db.Model):
    __tablename__ = 'avisos'
    id = db.Column(db.Integer, primary_key=True)
    programa_id = db.Column(db.Integer, db.ForeignKey('programas.id'), nullable=False)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Inscricao(db.Model):
    __tablename__ = 'inscricoes'
    id = db.Column(db.Integer, primary_key=True)

    # Campos comuns
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    telefone = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(2), nullable=False)

    # ✅ NOVO: Ano de inscrição
    ano_inscricao = db.Column(db.Integer, default=lambda: datetime.now().year, nullable=False)

    # Campos específicos em JSON
    campos_extras = db.Column(db.JSON, nullable=True)

    palestras_selecionadas = db.Column(db.JSON, nullable=True)
    presenca_palestras = db.Column(db.JSON, nullable=True)

    # Arquivos
    foto_filename = db.Column(db.String(255), nullable=True)
    curriculo_filename = db.Column(db.String(255), nullable=True)
    termo_responsabilidade_filename = db.Column(db.String(255), nullable=True)

    # Relacionamentos
    programa_id = db.Column(db.Integer, db.ForeignKey('programas.id'), nullable=False)
    status = db.Column(db.String(20), default='pendente', nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    certificado_enviado = db.Column(db.Boolean, default=False, nullable=False)


class ConfiguracaoEmail(db.Model):
    __tablename__ = 'configuracao_email'
    id = db.Column(db.Integer, primary_key=True)
    template_assunto = db.Column(db.String(255), nullable=False, default='Recebemos sua inscrição')
    template_corpo = db.Column(db.Text, nullable=False, default='Olá {nome},\n\nRecebemos sua inscrição para o programa {programa}.\n\nObrigada!\nComissão Feminina de Automobilismo - CFA Brasil')

    # Template de email de seleção POR PALESTRA (Imersão)
    template_selecao_assunto = db.Column(db.String(255), nullable=False, default='Confirmação de Seleção - {titulo_palestra}')
    template_selecao_corpo = db.Column(db.Text, nullable=False, default='Olá {nome},\n\nParabéns! Você foi selecionada para participar da palestra:\n\n📌 {titulo_palestra}\n📅 Data: {data_palestra}\n🕐 Horário: {horario_palestra}\n⏱️ Duração: {carga_horaria}\n👩‍🏫 Palestrante(s): {palestrantes}\n\n🔗 Link da sala Zoom: {link_zoom}\n\nNos vemos lá!\nComissão Feminina de Automobilismo - CFA Brasil')

    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ==================== FUNÇÕES AUXILIARES ====================
def allowed_file(filename: str, tipos=['img']) -> bool:
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if 'img' in tipos and ext in {'png', 'jpg', 'jpeg'}:
        return True
    if 'pdf' in tipos and ext == 'pdf':
        return True
    return False

def is_admin_logged_in() -> bool:
    return session.get('admin_logged_in') is True

def verificar_inscricao_duplicada(email, programa_id, ano):
    """Verifica se já existe inscrição para este email, programa e ano"""
    return Inscricao.query.filter_by(
        email=email,
        programa_id=programa_id,
        ano_inscricao=ano
    ).first()

def obter_historico_inscricoes(email):
    """Retorna todas as inscrições de um email"""
    return Inscricao.query.filter_by(email=email).order_by(
        Inscricao.ano_inscricao.desc(),
        Inscricao.criado_em.desc()
    ).all()

def enviar_email_confirmacao(inscricao: Inscricao):
    """Envia email simples de confirmação."""
    config = ConfiguracaoEmail.query.first()
    if not config:
        config = ConfiguracaoEmail()
        db.session.add(config)
        db.session.commit()

    assunto = config.template_assunto.format(
        nome=inscricao.nome,
        programa=inscricao.programa.nome
    )

    corpo = config.template_corpo.format(
        nome=inscricao.nome,
        programa=inscricao.programa.nome
    )

    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT', '587')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    smtp_from = f"CFA Brasil <{smtp_user}>"

    if not (smtp_host and smtp_user and smtp_pass):
        print('SMTP não configurado. Email não enviado.')
        return

    msg = EmailMessage()
    msg['Subject'] = assunto
    msg['From'] = smtp_from
    msg['To'] = inscricao.email
    msg.set_content(corpo)

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as e:
        print('Erro ao enviar email:', e)

def enviar_email_selecao(inscricao: Inscricao, palestras_especificas=None):
    return 0, 0
    """
    Envia um email POR PALESTRA para candidatas selecionadas do programa Imersão.

    Args:
        inscricao: Objeto Inscricao
        palestras_especificas: Lista opcional de IDs de palestras específicas para enviar.
                              Se None, envia para todas as palestras selecionadas.

    Retorna (total_enviados, total_erros)
    """
    #print(f"\n=== INICIANDO ENVIO DE EMAILS DE SELEÇÃO ===")
    #print(f"Candidata: {inscricao.nome} ({inscricao.email})")
    #print(f"Programa: {inscricao.programa.slug}")

    #if palestras_especificas:
        #print(f"🎯 Envio ESPECÍFICO apenas para: {palestras_especificas}")

    if inscricao.programa.slug != 'imersao':
        #print("❌ Não é programa Imersão")
        return 0, 0

    #print(f"Campos extras: {inscricao.campos_extras}")

    if not inscricao.campos_extras or 'palestras_selecionadas' not in inscricao.campos_extras:
        #print("❌ Sem palestras selecionadas nos campos extras")
        return 0, 0

    palestras_selecionadas = inscricao.campos_extras['palestras_selecionadas']
    #print(f"✓ Palestras selecionadas: {palestras_selecionadas}")

    if not palestras_selecionadas:
        #print("❌ Lista de palestras vazia")
        return 0, 0

    # Se foi especificado palestras específicas, filtrar
    if palestras_especificas:
        # Normalizar tanto as palestras da candidata quanto as do filtro
        palestras_selecionadas_normalizadas = [p.replace('_', '') for p in palestras_selecionadas]
        palestras_especificas_normalizadas = [p.replace('_', '') for p in palestras_especificas]

        #print(f"  Palestras candidata (normalizado): {palestras_selecionadas_normalizadas}")
        #print(f"  Filtro (normalizado): {palestras_especificas_normalizadas}")

        # Encontrar intersecção
        palestras_para_enviar = []
        for p_candidata in palestras_selecionadas:
            p_norm = p_candidata.replace('_', '')
            if p_norm in palestras_especificas_normalizadas:
                palestras_para_enviar.append(p_candidata)

        #print(f"✓ Após filtro: enviando apenas para {palestras_para_enviar}")

        if not palestras_para_enviar:
            #print("⚠️ Nenhuma palestra da candidata corresponde ao filtro")
            return 0, 0

        palestras_selecionadas = palestras_para_enviar

    config = ConfiguracaoEmail.query.first()
    if not config:
        config = ConfiguracaoEmail()
        db.session.add(config)
        db.session.commit()

    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT', '587')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    smtp_from = f"CFA Brasil <{smtp_user}>"

    if not (smtp_host and smtp_user and smtp_pass):
        #print('SMTP não configurado. Emails não enviados.')
        return 0, len(palestras_selecionadas)

    enviados = 0
    erros = 0

    # Enviar um email para cada palestra selecionada
    for palestra_id in palestras_selecionadas:
        # Normalizar o ID da palestra (aceitar 'palestra_1' ou 'palestra1')
        palestra_id_normalizado = palestra_id.replace('_', '')

        #print(f"\nProcessando: {palestra_id} -> normalizado para: {palestra_id_normalizado}")

        if palestra_id_normalizado not in PALESTRAS_IMERSAO:
            #print(f"❌ Palestra {palestra_id_normalizado} não encontrada no dicionário")
            #print(f"Palestras disponíveis: {list(PALESTRAS_IMERSAO.keys())}")
            erros += 1
            continue

        palestra = PALESTRAS_IMERSAO[palestra_id_normalizado]
        #print(f"✓ Palestra encontrada: {palestra['titulo']}")

        # Preparar dados da palestra
        assunto = config.template_selecao_assunto.format(
            nome=inscricao.nome,
            titulo_palestra=palestra['titulo']
        )

        corpo = config.template_selecao_corpo.format(
            nome=inscricao.nome,
            programa=inscricao.programa.nome,
            titulo_palestra=palestra['titulo'],
            data_palestra=palestra['data'],
            horario_palestra=palestra['horario'],
            carga_horaria=palestra['carga_horaria'],
            palestrantes=', '.join(palestra['palestrantes']),
            link_zoom=palestra.get('link_zoom', '[Link não configurado]')
        )

        msg = EmailMessage()
        msg['Subject'] = assunto
        msg['From'] = smtp_from
        msg['To'] = inscricao.email
        msg.set_content(corpo)

        try:
            with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            enviados += 1
            print(f'✓ Email enviado para {inscricao.email} - Palestra {palestra["numero"]}')
        except Exception as e:
            erros += 1
            print(f'✗ Erro ao enviar email para {inscricao.email} - Palestra {palestra["numero"]}: {e}')

    return enviados, erros



# ==================== FUNÇÕES DE CERTIFICADO ====================

def gerar_pdf_certificado_palestra(inscricao, palestra_id):
    """Gera certificado individual para uma palestra específica - Formato bilíngue"""

    if palestra_id not in PALESTRAS_IMERSAO:
        return None

    palestra = PALESTRAS_IMERSAO[palestra_id]

    buffer = BytesIO()
    largura, altura = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    # Cores
    cor_primaria = colors.HexColor('#da6b2d')
    cor_secundaria = colors.HexColor('#1a1a1a')
    cor_texto = colors.HexColor('#333333')
    cor_cinza = colors.HexColor('#6c757d')

    # OPÇÃO: Adicionar imagem de fundo do Canva (se você criar)
    template_path = os.path.join(BASE_DIR, 'static', 'certificado_template.png')
    if os.path.exists(template_path):
        c.drawImage(template_path, 0, 0, width=largura, height=altura, preserveAspectRatio=True)
    else:
        # Se não tiver template, criar borda simples
        c.setStrokeColor(cor_primaria)
        c.setLineWidth(4)
        c.rect(30, 30, largura-60, altura-60, stroke=1, fill=0)
        c.setLineWidth(1)
        c.rect(40, 40, largura-80, altura-80, stroke=1, fill=0)


    # ==================== TEXTO EM PORTUGUÊS ====================
    y_position = altura - 160  # Começa um pouco mais alto

    c.setFillColor(cor_texto)
    c.setFont("Helvetica", 13)

    # "Certificamos que"
    c.drawCentredString(largura/2, y_position, "Certificamos que")
    y_position -= 35  # Espaço para o nome

    # NOME DA CANDIDATA (destaque)
    c.setFillColor(cor_primaria)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(largura/2, y_position, inscricao.nome.upper())
    y_position -= 35  # AJUSTE AQUI: espaço maior após o nome

    # Texto principal em português
    c.setFillColor(cor_texto)
    c.setFont("Helvetica", 12)

    # Linha 1: "participou com êxito da atividade"
    c.drawCentredString(largura/2, y_position, "participou com êxito da atividade")
    y_position -= 22  # Espaço para o título da palestra

    # Linha 2: TÍTULO DA PALESTRA (destaque)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(cor_secundaria)
    titulo_palestra = palestra['titulo']

    # Quebrar título em múltiplas linhas se necessário
    max_width = largura - 150
    if c.stringWidth(titulo_palestra, "Helvetica-Bold", 14) > max_width:
        # Dividir em 2 linhas
        palavras = titulo_palestra.split()
        meio = len(palavras) // 2
        linha1 = " ".join(palavras[:meio])
        linha2 = " ".join(palavras[meio:])

        c.drawCentredString(largura/2, y_position, linha1)
        y_position -= 18
        c.drawCentredString(largura/2, y_position, linha2)
        y_position -= 22
    else:
        c.drawCentredString(largura/2, y_position, titulo_palestra)
        y_position -= 22

    # Linha 3: "realizada em [data], ministrada por"
    c.setFont("Helvetica", 12)
    c.setFillColor(cor_texto)

    # Converter data para formato extenso
    data_palestra = palestra['data']  # Ex: "02/02/2026"

    c.drawCentredString(largura/2, y_position, f"realizada em {data_palestra}, ministrada por")
    y_position -= 18

    # Linha 4: PALESTRANTES
    palestrantes_texto = ", ".join(palestra['palestrantes'])

    # Quebrar palestrantes em múltiplas linhas se necessário
    c.setFont("Helvetica-Bold", 11)
    if c.stringWidth(palestrantes_texto, "Helvetica-Bold", 11) > max_width:
        palavras_pal = palestrantes_texto.split()
        linha_atual = ""

        for palavra in palavras_pal:
            teste = linha_atual + palavra + " "
            if c.stringWidth(teste, "Helvetica-Bold", 11) < max_width:
                linha_atual = teste
            else:
                c.drawCentredString(largura/2, y_position, linha_atual.strip())
                linha_atual = palavra + " "
                y_position -= 15

        if linha_atual:
            c.drawCentredString(largura/2, y_position, linha_atual.strip())
            y_position -= 20
    else:
        c.drawCentredString(largura/2, y_position, palestrantes_texto)
        y_position -= 20

    # Linha 5: "durante o IMERSÃO MULHERES NO MOTORSPORT"
    c.setFont("Helvetica", 12)
    c.setFillColor(cor_texto)
    c.drawCentredString(largura/2, y_position, "durante a IMERSÃO MULHERES NO MOTORSPORT,")
    y_position -= 18

    # Linha 6: "contabilizando carga horária total de 2h."
    c.drawCentredString(largura/2, y_position, "contabilizando carga horária total de 2h.")
    y_position -= 35

    # ==================== TEXTO EM INGLÊS ====================
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(cor_cinza)

    # Linha 1 (inglês)
    c.drawCentredString(largura/2, y_position, f"We certify that {inscricao.nome} successfully participated in the activity")
    y_position -= 14

    # Linha 2 (inglês) - Título da palestra
    c.setFont("Helvetica-BoldOblique", 10)
    if c.stringWidth(titulo_palestra, "Helvetica-BoldOblique", 10) > max_width:
        palavras = titulo_palestra.split()
        meio = len(palavras) // 2
        linha1 = " ".join(palavras[:meio])
        linha2 = " ".join(palavras[meio:])

        c.drawCentredString(largura/2, y_position, linha1)
        y_position -= 12
        c.drawCentredString(largura/2, y_position, linha2)
        y_position -= 14
    else:
        c.drawCentredString(largura/2, y_position, titulo_palestra)
        y_position -= 14

    # Linha 3 (inglês)
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(largura/2, y_position, f"carried out on {data_palestra}, during the IMERSÃO MULHERES NO MOTORSPORT,")
    y_position -= 12

    # Linha 4 (inglês)
    c.drawCentredString(largura/2, y_position, "accounting for a total workload of 2h.")

    # ==================== RODAPÉ ====================
    # Data de emissão
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

    c.drawCentredString(largura/2, 60, f"Emitido em, {data_emissao}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer




def enviar_certificados_email(inscricao):
    """Envia certificados apenas para palestras selecionadas E com presença confirmada"""

    # VERIFICAR: Apenas Imersão + Selecionada
    if inscricao.programa.slug != 'imersao':
        return False, "Certificados apenas para Imersão"

    if inscricao.status != 'selecionada':
        return False, "Certificados apenas para candidatas selecionadas"

    # Usar palestras_selecionadas (campo novo do admin)
    if not inscricao.palestras_selecionadas or len(inscricao.palestras_selecionadas) == 0:
        return False, "Nenhuma palestra selecionada para esta candidata"

    # Filtrar apenas palestras com presença confirmada
    presenca_palestras = inscricao.presenca_palestras or {}
    palestras_com_presenca = [
        p for p in inscricao.palestras_selecionadas
        if presenca_palestras.get(p, False)
    ]

    if not palestras_com_presenca:
        return False, "Nenhuma presença confirmada ainda. A candidata {inscricao.nome} precisa ter pelo menos uma palestra marcada como 'presente' para receber certificados."

    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    smtp_from = f"CFA Brasil <{smtp_user}>"

    if not (smtp_host and smtp_user and smtp_pass):
        return False, "SMTP não configurado"

    msg = EmailMessage()
    msg['Subject'] = f"Certificados - CFA Brasil - Imersão 2026"
    msg['From'] = smtp_from
    msg['To'] = inscricao.email

    corpo = f"""Olá {inscricao.nome},

Parabéns por sua participação no Programa Imersão para Mulheres no Motorsport 2026!

Seguem em anexo seus certificados de participação nas palestras:

"""

    for palestra_id in palestras_com_presenca:
        if palestra_id in PALESTRAS_IMERSAO:
            palestra = PALESTRAS_IMERSAO[palestra_id]
            corpo += f"• Palestra {palestra['numero']}: {palestra['titulo']}\n"

    corpo += """
Continue quebrando barreiras e abrindo portas no automobilismo!

Comissão Feminina de Automobilismo - CFA Brasil"""

    msg.set_content(corpo)

    # Anexar certificados apenas das palestras com presença
    for palestra_id in palestras_com_presenca:
        if palestra_id in PALESTRAS_IMERSAO:
            pdf_buffer = gerar_pdf_certificado_palestra(inscricao, palestra_id)

            if pdf_buffer:
                palestra = PALESTRAS_IMERSAO[palestra_id]
                nome_arquivo = f"Certificado_Palestra{palestra['numero']}.pdf"
                msg.add_attachment(
                    pdf_buffer.getvalue(),
                    maintype='application',
                    subtype='pdf',
                    filename=nome_arquivo
                )

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            inscricao.certificado_enviado = True
            db.session.commit()
        return True, f"Certificados enviados com sucesso ({len(palestras_com_presenca)} palestras)!"
    except Exception as e:
        return False, f"Erro ao enviar: {str(e)}"



# ==================== PROCESSAMENTO DE CAMPOS ESPECÍFICOS ====================
def processar_campos_kart(form, erros):
    campos = {}
    campos['data_nascimento'] = form.get('data_nascimento', '').strip()
    campos['cor'] = form.get('cor', '').strip()
    campos['nome_responsavel'] = form.get('nome_responsavel', '').strip()
    campos['telefone_responsavel'] = form.get('telefone_responsavel', '').strip()
    campos['tem_condicoes_logistica'] = form.get('tem_condicoes_logistica', '').strip()
    campos['categoria'] = form.get('categoria', '').strip()
    campos['peso'] = form.get('peso', '').strip()
    campos['altura'] = form.get('altura', '').strip()
    campos['vestuario'] = form.getlist('vestuario')
    campos['categoria_atual'] = form.get('categoria_atual', '').strip()
    campos['titulos_resultados'] = form.get('titulos_resultados', '').strip()
    campos['autorizacao_responsavel'] = form.get('autorizacao_responsavel') == 'on'
    return campos

def processar_campos_imersao(form, erros):
    campos = {}
    campos['idade'] = form.get('idade', '').strip()
    campos['escolaridade'] = form.get('escolaridade', '').strip()
    campos['participou_antes'] = form.get('participou_antes', '').strip()
    campos['como_ficou_sabendo'] = form.get('como_ficou_sabendo', '').strip()

    # NOVO: Palestras selecionadas (substituindo módulo_interesse)
    palestras_selecionadas = form.getlist('palestras')
    if not palestras_selecionadas:
        erros.append('Você precisa selecionar pelo menos uma palestra.')
    campos['palestras_selecionadas'] = palestras_selecionadas

    return campos


def processar_campos_estagio(form, erros):
    campos = {}
    campos['data_nascimento'] = form.get('data_nascimento', '').strip()
    campos['identidade_genero'] = form.get('identidade_genero', '').strip()
    campos['cor'] = form.get('cor', '').strip()
    campos['participou_fia_got'] = form.get('participou_fia_got', '').strip()
    campos['area_atuacao'] = form.get('area_atuacao', '').strip()
    campos['ativacoes'] = form.getlist('ativacoes')
    campos['ordem_preferencia'] = form.get('ordem_preferencia', '').strip()
    campos['tem_cnh'] = form.get('tem_cnh', '').strip()
    campos['linkedin'] = form.get('linkedin', '').strip()
    campos['mini_bio'] = form.get('mini_bio', '').strip()
    campos['porque_importante'] = form.get('porque_importante', '').strip()
    campos['como_ficou_sabendo'] = form.get('como_ficou_sabendo', '').strip()
    campos['concordo_compartilhamento'] = form.get('concordo_compartilhamento') == 'on'


    return campos

def processar_campos_wec(form, erros):
    campos = {}
    campos['data_nascimento'] = form.get('data_nascimento', '').strip()
    campos['identidade_genero'] = form.get('identidade_genero', '').strip()
    campos['cor'] = form.get('cor', '').strip()
    campos['participou_fia_got'] = form.get('participou_fia_got', '').strip()
    campos['area_atuacao'] = form.get('area_atuacao', '').strip()
    campos['ativacoes'] = form.getlist('ativacoes')
    campos['ordem_preferencia'] = form.get('ordem_preferencia', '').strip()
    campos['tem_cnh'] = form.get('tem_cnh', '').strip()
    campos['linkedin'] = form.get('linkedin', '').strip()
    campos['mini_bio'] = form.get('mini_bio', '').strip()
    campos['porque_importante'] = form.get('porque_importante', '').strip()
    campos['como_ficou_sabendo'] = form.get('como_ficou_sabendo', '').strip()
    campos['concordo_compartilhamento'] = form.get('concordo_compartilhamento') == 'on'
    return campos


def processar_campos_esports(form, erros):
    campos = {}
    campos['idade'] = form.get('idade', '').strip()
    campos['cidade'] = form.get('cidade', '').strip()
    campos['nickname'] = form.get('nickname', '').strip()
    campos['plataforma'] = form.get('plataforma', '').strip()
    campos['experiencia'] = form.get('experiencia', '').strip()
    return campos

# ==================== ROTAS PÚBLICAS ====================
@app.route('/')
def index():
    programas = Programa.query.filter_by(ativo=True).all()
    return render_template('index.html', programas=programas, hoje=date.today())

@app.route('/programa/<slug>')
def programa_detalhe(slug):
    programa = Programa.query.filter_by(slug=slug, ativo=True).first_or_404()
    hoje = date.today()
    aberto = True
    if programa.data_abertura and hoje < programa.data_abertura:
        aberto = False
    if programa.data_fechamento and hoje > programa.data_fechamento:
        aberto = False
    avisos = Aviso.query.filter_by(programa_id=programa.id, ativo=True).all()
    return render_template('programa.html', programa=programa, avisos=avisos, aberto=aberto, hoje=hoje)

@app.route('/inscricao/<slug>', methods=['GET', 'POST'])
def inscricao(slug):
    programa = Programa.query.filter_by(slug=slug, ativo=True).first_or_404()
    hoje = date.today()
    ano_atual = datetime.now().year

    if programa.data_abertura and hoje < programa.data_abertura:
        flash('Inscrições ainda não foram abertas para este programa.', 'warning')
        return redirect(url_for('programa_detalhe', slug=slug, _external=True, _scheme='https'))
    if programa.data_fechamento and hoje > programa.data_fechamento:
        flash('Inscrições encerradas para este programa.', 'warning')
        return redirect(url_for('programa_detalhe', slug=slug, _external=True, _scheme='https'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        estado = request.form.get('estado', '').strip().upper()


        erros = []
        if not nome:
            erros.append('Nome é obrigatório.')
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            erros.append('Email inválido.')
        if not telefone:
            erros.append('Telefone é obrigatório.')
        if not estado or len(estado) != 2:
            erros.append('Estado (UF) é obrigatório.')

        # ✅ VERIFICAR DUPLICATA
        duplicata = verificar_inscricao_duplicada(email, programa.id, ano_atual)
        if duplicata:
            flash(f'Você já se inscreveu no programa "{programa.nome}" em {ano_atual}. Não é possível se inscrever novamente no mesmo programa no mesmo ano.', 'danger')
            return redirect(url_for('programa_detalhe', slug=slug, _external=True, _scheme='https'))

        # Processar campos específicos
        campos_extras = {}
        if programa.slug == 'kart':
            campos_extras = processar_campos_kart(request.form, erros)
        elif programa.slug == 'imersao':
            campos_extras = processar_campos_imersao(request.form, erros)
        elif programa.slug == 'estagio-motorsport':
            campos_extras = processar_campos_estagio(request.form, erros)
        elif programa.slug == 'experiencia-wec':
            campos_extras = processar_campos_wec(request.form, erros)
        elif programa.slug == 'e-sports':
            campos_extras = processar_campos_esports(request.form, erros)

        # Upload de arquivos
        foto_filename = None
        curriculo_filename = None
        termo_filename = None

        if programa.slug in ['kart', 'estagio-motorsport']:
            foto = request.files.get('foto')
            if foto and allowed_file(foto.filename, ['img']):
                original = secure_filename(foto.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
                foto_filename = f"{timestamp}_{original}"
                foto.save(os.path.join(app.config['UPLOAD_FOLDER'], foto_filename))

        if programa.slug in ['estagio-motorsport', 'experiencia-wec']:
            curriculo = request.files.get('curriculo')
            if curriculo and allowed_file(curriculo.filename, ['pdf']):
                original = secure_filename(curriculo.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
                curriculo_filename = f"{timestamp}_{original}"
                curriculo.save(os.path.join(app.config['UPLOAD_FOLDER'], curriculo_filename))
        termo = request.files.get('termo_responsabilidade')
        if not termo or not allowed_file(termo.filename, ['pdf']):
            erros.append('Termo de Responsabilidade assinado e em PDF é obrigatório.')
        else:
            original = secure_filename(termo.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
            termo_filename = f"{timestamp}_{original}"
            termo.save(os.path.join(app.config['UPLOAD_FOLDER'], termo_filename))
        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('inscricao.html', programa=programa)

        inscricao_obj = Inscricao(
            nome=nome,
            email=email,
            telefone=telefone,
            estado=estado,
            ano_inscricao=ano_atual,
            campos_extras=campos_extras,
            foto_filename=foto_filename,
            curriculo_filename=curriculo_filename, termo_responsabilidade_filename=termo_filename,
            programa_id=programa.id,
            status='pendente'
        )

        db.session.add(inscricao_obj)
        db.session.commit()

        enviar_email_confirmacao(inscricao_obj)

        flash('Inscrição realizada com sucesso! Você receberá um email de confirmação.', 'success')
        return redirect(url_for('programa_detalhe', slug=slug, _external=True, _scheme='https'))

        # Passar dados das palestras para o template se for Imersão
    palestras = PALESTRAS_IMERSAO if programa.slug == 'imersao' else None

    return render_template('inscricao.html', programa=programa, palestras=palestras)


# ==================== ROTAS ADMIN ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()  # Na verdade é username agora
        senha = request.form.get('senha', '').strip()

        admin = AdminUser.query.filter_by(email=email).first()

        if not admin or not check_password_hash(admin.password_hash, senha):
            flash('Credenciais inválidas.', 'danger')
            return render_template('admin_login.html')

        session['admin_logged_in'] = True
        session['admin_email'] = admin.email
        flash('Login realizado com sucesso.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_login.html')

@app.route('/admin/certificado/<int:inscricao_id>')
def gerar_certificado(inscricao_id):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    inscricao = Inscricao.query.get_or_404(inscricao_id)

    if inscricao.programa.slug != 'imersao':
        flash('Certificados disponíveis apenas para o programa Imersão.', 'warning')
        return redirect(url_for('admin_dashboard'))

    if inscricao.status != 'selecionada':
        flash('Certificado disponível apenas para candidatas selecionadas.', 'warning')
        return redirect(url_for('admin_dashboard'))

    buffer = gerar_pdf_certificado(inscricao)
    filename = f"certificado_{inscricao.nome.replace(' ', '_')}.pdf"

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


def gerar_pdf_certificado(inscricao: Inscricao):
    """Gera o PDF do certificado"""
    buffer = BytesIO()
    largura, altura = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    cor_primaria = colors.HexColor('#E10600')
    cor_secundaria = colors.HexColor('#1a1a1a')
    cor_texto = colors.HexColor('#333333')

    # Borda
    c.setStrokeColor(cor_primaria)
    c.setLineWidth(3)
    c.rect(30, 30, largura-60, altura-60, stroke=1, fill=0)

    # Título
    c.setFillColor(cor_primaria)
    c.setFont("Helvetica-Bold", 48)
    titulo = "CERTIFICADO"
    c.drawCentredString(largura/2, altura - 100, titulo)

    # Subtítulo
    c.setFillColor(cor_secundaria)
    c.setFont("Helvetica", 18)
    c.drawCentredString(largura/2, altura - 130, "CFA Brasil - Comissão Feminina de Automobilismo")

    # Nome
    c.setFillColor(cor_primaria)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(largura/2, altura - 250, inscricao.nome.upper())

    # Texto
    c.setFillColor(cor_texto)
    c.setFont("Helvetica", 16)
    c.drawCentredString(largura/2, altura - 300, "participou com aproveitamento do programa")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(largura/2, altura - 330, "Imersão para Mulheres no Motorsport")

    # Data
    c.setFont("Helvetica", 12)
    data_emissao = datetime.now().strftime("%d de %B de %Y")
    meses = {
        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
        'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
        'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
        'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
    }
    for en, pt in meses.items():
        data_emissao = data_emissao.replace(en, pt)

    c.drawCentredString(largura/2, 150, f"Brasil, {data_emissao}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Logout realizado com sucesso.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    programas = Programa.query.order_by(Programa.nome).all()
    query = Inscricao.query.join(Programa)

    # ✅ FILTROS AVANÇADOS
    programa_id = request.args.get('programa_id')
    ano = request.args.get('ano')
    nome = request.args.get('nome')
    email = request.args.get('email')
    status = request.args.get('status')
    estado = request.args.get('estado')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    inscricoes_multiplas = request.args.get('inscricoes_multiplas')

    # 🆕 NOVOS FILTROS PARA ESTÁGIO MOTORSPORT
    filtro_area = request.args.get('area_atuacao')
    filtro_idade_min = request.args.get('idade_min')
    filtro_idade_max = request.args.get('idade_max')
    filtro_escolaridade = request.args.get('escolaridade')
    filtro_cor = request.args.get('cor')
    filtroativacoes = request.args.getlist('ativacoes')  # Lista de ativações selecionadas
    filtro_presenca = request.args.get('filtro_presenca')
    filtro_certificado = request.args.get('filtro_certificado')
    if filtro_certificado == 'nao_enviado_com_presenca':
        query = query.filter(
            Inscricao.certificado_enviado == False,  # NÃO enviado
            Inscricao.palestras_selecionadas.isnot(None),  # Tem palestras
            Inscricao.presenca_palestras.isnot(None),      # Tem presença
            Inscricao.programa.has(slug='imersao'),        # Imerso
            Inscricao.status == 'selecionada'              # Selecionada
        )


    if programa_id and programa_id.isdigit():
        query = query.filter(Inscricao.programa_id == int(programa_id))

    if ano and ano.isdigit():
        query = query.filter(Inscricao.ano_inscricao == int(ano))

    if nome:
        query = query.filter(Inscricao.nome.ilike(f'%{nome}%'))

    if email:
        query = query.filter(Inscricao.email.ilike(f'%{email}%'))

    if filtro_presenca == 'com_presenca':
        query = query.filter(
            Inscricao.palestras_selecionadas.isnot(None),
            Inscricao.presenca_palestras.isnot(None)
        )

    status = request.args.get('status')

    status_lista = request.args.getlist('status')  # Pega múltiplos valores
    if status_lista:
        # Filtrar apenas valores válidos
        status_validos = [s for s in status_lista if s in ['pendente', 'pre_selecionada', 'selecionada', 'nao_selecionada', 'backup']]
        if status_validos:
            query = query.filter(Inscricao.status.in_(status_validos))


    if estado:
        query = query.filter(Inscricao.estado == estado.upper())

    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Inscricao.criado_em >= data_inicio_obj)
        except:
            pass

    if data_fim:
        try:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
            query = query.filter(Inscricao.criado_em <= data_fim_obj)
        except:
            pass


    inscricoes = query.order_by(Inscricao.criado_em.desc()).all()

    # FILTRO: Palestra específica (apenas para Imersão)
    palestra_id = request.args.get('palestra')
    if palestra_id:
        inscricoes_filtradas = []
        for inscricao in inscricoes:
            # Verificar se é do programa Imersão e tem palestras selecionadas
            if (inscricao.programa.slug == 'imersao' and
                inscricao.campos_extras and
                'palestras_selecionadas' in inscricao.campos_extras):

                palestras = inscricao.campos_extras['palestras_selecionadas']
                if palestra_id in palestras:
                    inscricoes_filtradas.append(inscricao)

        inscricoes = inscricoes_filtradas


    # FILTRO: PALESTRA (aplicar ANTES de buscar, se possível)
    palestra_filtro = request.args.get('palestra')
    inscricoes_multiplas = request.args.get('inscricoes_multiplas')


    # FILTRO DE INSCRIÇÕES MÚLTIPLAS
    if inscricoes_multiplas == 'sim':
        emails_multiplos = db.session.query(Inscricao.email).group_by(Inscricao.email).having(db.func.count(Inscricao.id) > 1).all()
        emails_multiplos = [e[0] for e in emails_multiplos]
        inscricoes = [i for i in inscricoes if i.email in emails_multiplos]

    if filtro_idade_min or filtro_idade_max:
        # DEBUG: Imprimir o que tem nos camposextras
        print("\n=== DEBUG FILTRO DE IDADE ===")
        print(f"filtro_idade_min: {filtro_idade_min}")
        print(f"filtro_idade_max: {filtro_idade_max}")
        print(f"Total de inscrições antes do filtro: {len(inscricoes)}")

        for i, inscricao in enumerate(inscricoes[:5]):  # Primeiras 5
            print(f"\nInscrição {i+1}: {inscricao.nome}")
            print(f"  - Programa: {inscricao.programa.slug}")
            print(f"  - Tem campos_extras? {bool(inscricao.campos_extras)}")
            if inscricao.campos_extras:
                print(f"  - Chaves em campos_extras: {list(inscricao.campos_extras.keys())}")
                print(f"  - data_nascimento: {inscricao.campos_extras.get('data_nascimento')}")
                print(f"  - data_nascimento: {inscricao.campos_extras.get('data_nascimento')}")
                print(f"  - idade: {inscricao.campos_extras.get('idade')}")

                # Testar calcularidade
                dn = inscricao.campos_extras.get('data_nascimento')
                if dn:
                    try:
                        idade_calc = calcular_idade(dn)
                        print(f"  - idade calculada de 'data_nascimento': {idade_calc}")
                    except Exception as e:
                        print(f"  - ERRO ao calcular idade: {e}")

        print("\n=============================\n")

        # CONTINUA COM O FILTRO NORMAL AQUI...
        inscricoes_filtradas = []

        # 🆕 FILTRO DE IDADE - APLICAR PARA TODOS OS PROGRAMAS

        if filtro_idade_min or filtro_idade_max:
            inscricoes_filtradas = []
            for inscricao in inscricoes:
                idade_encontrada = None

                if inscricao.campos_extras:
                    campos = inscricao.campos_extras

                    # Tentar data_nascimento (com underscore) - Kart e Estágio
                    data_nascimento = campos.get('data_nascimento') or campos.get('datanascimento')

                    if data_nascimento:
                        idade_encontrada = calcular_idade(data_nascimento)

                    # Se não achou, tentar campo idade direto (e-sports e Imersão)
                    if idade_encontrada is None:
                        idade_direta = campos.get('idade')
                        if idade_direta:
                            try:
                                idade_encontrada = int(idade_direta)
                            except (ValueError, TypeError):
                                pass

                # Aplicar filtro se encontrou idade
                if idade_encontrada is not None:
                    incluir = True

                    if filtro_idade_min:
                        if idade_encontrada < int(filtro_idade_min):
                            incluir = False

                    if filtro_idade_max:
                        if idade_encontrada > int(filtro_idade_max):
                            incluir = False

                    if incluir:
                        inscricoes_filtradas.append(inscricao)

            inscricoes = inscricoes_filtradas



    # FILTRO POR PALESTRA ESPECÍFICA (apenas Imersão)
    if palestra_filtro:
        inscricoes_filtradas = []

        for ins in inscricoes:
            if ins.programa.slug == 'imersao':
                if ins.campos_extras:
                    palestras_candidata = ins.campos_extras.get('palestras_selecionadas', [])

                    # Normalizar IDs (aceitar palestra1 ou palestra_1)
                    palestras_normalizadas = [p.replace('_', '') for p in palestras_candidata]

                    if palestra_filtro in palestras_normalizadas:
                        inscricoes_filtradas.append(ins)

        inscricoes = inscricoes_filtradas

    # 🆕 APLICAR FILTROS ESPECÍFICOS DO ESTÁGIO MOTORSPORT / EXPERIÊNCIA WEC
    SLUGS_MOTORSPORT = {'estagio-motorsport', 'experiencia-wec'}
    programa_motorsport = Programa.query.filter(Programa.slug.in_(SLUGS_MOTORSPORT)).first()

    # Se filtrou por motorsport/WEC OU se não filtrou por programa mas há filtros específicos
    aplicar_filtros_motorsport = False
    programa_motorsport_ids = [p.id for p in Programa.query.filter(Programa.slug.in_(SLUGS_MOTORSPORT)).all()]
    if programa_id and int(programa_id) in programa_motorsport_ids:
        aplicar_filtros_motorsport = True
    elif not programa_id and (filtro_escolaridade or filtro_cor or filtroativacoes or filtro_area):
        # Se não filtrou programa mas há filtros específicos, filtrar apenas programas motorsport/WEC
        inscricoes = [i for i in inscricoes if i.programa.slug in SLUGS_MOTORSPORT]
        aplicar_filtros_motorsport = True

    if aplicar_filtros_motorsport:
        inscricoes_filtradas = []

        for inscricao in inscricoes:
            # Garantir que é motorsport/WEC e tem campos_extras
            if inscricao.programa.slug not in SLUGS_MOTORSPORT or not inscricao.campos_extras:
                continue

            campos = inscricao.campos_extras
            incluir = True

            # FILTRO POR IDADE


            # FILTRO POR ESCOLARIDADE
            if filtro_escolaridade and incluir:
                escolaridade = campos.get('escolaridade', '').lower()
                if filtro_escolaridade.lower() not in escolaridade:
                    incluir = False

            # FILTRO POR COR
            if filtro_cor and incluir:
                cor = campos.get('cor', '').lower()
                if filtro_cor.lower() != cor:
                    incluir = False

            # FILTRO POR ÁREA DE ATUAÇÃO
            if filtro_area and incluir:
                area_atuacao = campos.get('area_atuacao', '').lower()
                if filtro_area.lower() not in area_atuacao:
                    incluir = False

            # FILTRO POR ATIVAÇÃO (status ativo/inativo no programa)
            if filtroativacoes and incluir:
                # Verificar se a candidata selecionou alguma das ativações filtradas
                ativacoes_candidata = campos.get('ativacoes', [])

                # Se o campo for string (caso antigo), converter para lista
                if isinstance(ativacoes_candidata, str):
                    ativacoes_candidata = [ativacoes_candidata]

                # Verificar se há intersecção entre as ativações da candidata e as filtradas
                tem_ativacao = any(ativacao in ativacoes_candidata for ativacao in filtroativacoes)

                if not tem_ativacao:
                    incluir = False


            if incluir:
                inscricoes_filtradas.append(inscricao)

        inscricoes = inscricoes_filtradas

    # FILTRO: Limitar às X primeiras (mais antigas)
    limite_inscricoes = request.args.get('limite')
    if limite_inscricoes and limite_inscricoes.isdigit():
        limite = int(limite_inscricoes)
        if limite > 0:
            # Ordenar por mais antigas primeiro quando há limite
            inscricoes = sorted(inscricoes, key=lambda x: x.criado_em)[:limite]
        else:
            inscricoes = sorted(inscricoes, key=lambda x: x.criado_em, reverse=True)
    else:
        inscricoes = sorted(inscricoes, key=lambda x: x.criado_em, reverse=True)


    # ✅ ADICIONAR HISTÓRICO A CADA INSCRIÇÃO
    for inscricao in inscricoes:
        inscricao.historico = obter_historico_inscricoes(inscricao.email)
        inscricao.total_inscricoes = len(inscricao.historico)

    # Estatísticas
    stats = {
        'pendentes': Inscricao.query.filter_by(status='pendente').count(),
        'pre_selecionadas': Inscricao.query.filter_by(status='pre_selecionada').count(),
        'backup': Inscricao.query.filter_by(status='backup').count(),
        'selecionadas': Inscricao.query.filter_by(status='selecionada').count(),
        'nao_selecionadas': Inscricao.query.filter_by(status='nao_selecionada').count(),
        'certificado_enviado': Inscricao.query.filter_by(certificado_enviado=True).count(),
        'total': Inscricao.query.count(),
        'certificado_nao_enviado': Inscricao.query.filter(
            Inscricao.certificado_enviado == False,
            Inscricao.programa.has(slug='imersao'),
            Inscricao.status == 'selecionada'
        ).count(),
        'stats_prontas': Inscricao.query.filter(Inscricao.certificado_enviado == False, Inscricao.palestras_selecionadas.isnot(None), Inscricao.presenca_palestras.isnot(None)
        ).count()
    }

    # Anos disponíveis
    anos_disponiveis = db.session.query(Inscricao.ano_inscricao).distinct().order_by(Inscricao.ano_inscricao.desc()).all()
    anos_disponiveis = [a[0] for a in anos_disponiveis]

    # Estados disponíveis
    estados_disponiveis = db.session.query(Inscricao.estado).distinct().order_by(Inscricao.estado).all()
    estados_disponiveis = [e[0] for e in estados_disponiveis]

    # OPÇÕES PARA FILTROS DE MOTORSPORT - mesmas do formulário de inscrição
    escolaridadesdisponiveis = [
        'Ensino Médio - Cursando',
        'Ensino Médio - Completo',
        'Ensino Superior - Cursando',
        'Ensino Superior - Completo',
        'Pós-Graduação'
    ]

    coresdisponiveis = [
        'Branca',
        'Preta',
        'Parda',
        'Amarela',
        'Indígena',
        'Prefiro não declarar'
    ]
    programamotorsport = Programa.query.filter_by(slug='estagio-motorsport').first()

    return render_template(
        'admin_dashboard.html',
        programas=programas,
        inscricoes=inscricoes,
        filtros=request.args,
        stats=stats,
        stats_geral=stats,
        anos_disponiveis=anos_disponiveis,
        estados_disponiveis=estados_disponiveis,
        palestras_imersao=PALESTRAS_IMERSAO,
        palestras_lista=PALESTRAS_IMERSAO,
        escolaridadesdisponiveis=escolaridadesdisponiveis,  # 🆕
        coresdisponiveis=coresdisponiveis,  # 🆕
        programa_motorsport_id=programa_motorsport.id if programa_motorsport else None,
        programa_motorsport_ids=programa_motorsport_ids

    )


# ✅ NOVA ROTA: EXPORTAR PDF COM FILTROS
@app.route('/admin/exportar-pdf')
def admin_exportar_pdf_filtrado():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

        # Aplicar mesmos filtros do dashboard
    query = Inscricao.query.join(Programa)

    # Filtros básicos
    programa_id = request.args.get('programa_id') or request.args.get('programaid')
    ano = request.args.get('ano')
    nome = request.args.get('nome')
    email = request.args.get('email')
    status_lista = request.args.getlist('status')
    estado = request.args.get('estado')
    data_inicio = request.args.get('data_inicio') or request.args.get('datainicio')
    data_fim = request.args.get('data_fim') or request.args.get('datafim')

    # Filtros específicos do Estágio Motorsport - ACEITAR AMBOS OS NOMES
    filtro_area = request.args.get('areaatuacao') or request.args.get('area_atuacao')
    filtro_area = filtro_area if filtro_area and filtro_area.strip() != '' and filtro_area != 'Todas' else None

    filtro_escolaridade = request.args.get('escolaridade')
    filtro_escolaridade = filtro_escolaridade if filtro_escolaridade and filtro_escolaridade.strip() != '' and filtro_escolaridade != 'Todas' else None

    filtro_cor = request.args.get('cor')
    filtro_cor = filtro_cor if filtro_cor and filtro_cor.strip() != '' and filtro_cor != 'Todas' else None

    filtro_ativacoes = request.args.getlist('ativacoes')

    filtro_idade_min = request.args.get('idademin') or request.args.get('idade_min')
    filtro_idade_min = filtro_idade_min if filtro_idade_min and filtro_idade_min.strip() != '' else None

    filtro_idade_max = request.args.get('idademax') or request.args.get('idade_max')
    filtro_idade_max = filtro_idade_max if filtro_idade_max and filtro_idade_max.strip() != '' else None

    filtro_limite = request.args.get('limite')
    filtro_limite = int(filtro_limite) if filtro_limite and filtro_limite.isdigit() else None


    # Aplicar filtros básicos na query
    if programa_id and programa_id.isdigit():
        query = query.filter(Inscricao.programa_id == int(programa_id))
    if ano and ano.isdigit():
        query = query.filter(Inscricao.ano_inscricao == int(ano))
    if nome:
        query = query.filter(Inscricao.nome.ilike(f'%{nome}%'))
    if email:
        query = query.filter(Inscricao.email.ilike(f'%{email}%'))

    if status_lista:
        status_validos = [s for s in status_lista if s in ['pendente', 'pre_selecionada', 'nao_selecionada', 'selecionada', 'backup']]
        if status_validos:
            query = query.filter(Inscricao.status.in_(status_validos))

    if estado:
        query = query.filter(Inscricao.estado == estado.upper())
    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Inscricao.criado_em >= data_inicio_obj)
        except:
            pass
    if data_fim:
        try:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
            query = query.filter(Inscricao.criado_em <= data_fim_obj)
        except:
            pass

    # Buscar todas as inscrições
    inscricoes = query.order_by(Inscricao.ano_inscricao.desc(), Inscricao.criado_em.desc()).all()



    # Verificar se precisa aplicar filtros específicos do Estágio Motorsport
    programa_motorsport = Programa.query.filter_by(slug='estagio-motorsport').first()
    aplicar_filtros_motorsport = False

    if programa_id and programa_motorsport and int(programa_id) == programa_motorsport.id:
        aplicar_filtros_motorsport = True

    elif not programa_id and (filtro_escolaridade or filtro_cor or filtro_ativacoes or filtro_area):
        inscricoes = [i for i in inscricoes if i.programa.slug == 'estagio-motorsport']
        aplicar_filtros_motorsport = True


    # Aplicar filtros específicos do Estágio Motorsport
    if aplicar_filtros_motorsport:
        inscricoes_filtradas = []

        for inscricao in inscricoes:
            if inscricao.programa.slug != 'estagio-motorsport' or not inscricao.campos_extras:
                continue

            campos = inscricao.campos_extras
            incluir = True

            # Filtro de escolaridade
            if filtro_escolaridade and incluir:
                escolaridade = campos.get('escolaridade', '')
                if escolaridade:
                    if filtro_escolaridade.lower() not in escolaridade.lower():
                        incluir = False

            # Filtro de cor/raça
            if filtro_cor and incluir:
                cor = campos.get('cor', '')
                if cor:
                    if filtro_cor.lower() != cor.lower():
                        incluir = False

            # Filtro de área de atuação
            if filtro_area and incluir:
                area_atuacao = campos.get('area_atuacao', '')
                if area_atuacao:
                    if filtro_area.lower() not in area_atuacao.lower():
                        incluir = False


            # Filtro de ativações
            if filtro_ativacoes and incluir:
                ativacoes_candidata = campos.get('ativacoes', [])
                if isinstance(ativacoes_candidata, str):
                    ativacoes_candidata = [ativacoes_candidata]
                tem_ativacao = any(ativacao in ativacoes_candidata for ativacao in filtro_ativacoes)
                if not tem_ativacao:
                    incluir = False

            # Filtro de idade
            if (filtro_idade_min or filtro_idade_max) and incluir:
                idade_encontrada = None

                data_nascimento = campos.get('data_nascimento') or campos.get('datanascimento')
                if data_nascimento:
                    try:
                        idade_encontrada = calcular_idade(data_nascimento)
                    except:
                        pass

                if idade_encontrada is None:
                    idade_direta = campos.get('idade')
                    if idade_direta:
                        try:
                            idade_encontrada = int(idade_direta)
                        except (ValueError, TypeError):
                            pass

                if idade_encontrada is not None:
                    if filtro_idade_min:
                        if idade_encontrada < int(filtro_idade_min):
                            incluir = False
                    if filtro_idade_max:
                        if idade_encontrada > int(filtro_idade_max):
                            incluir = False

            if incluir:
                inscricoes_filtradas.append(inscricao)

        inscricoes = inscricoes_filtradas


    # Aplicar limite se especificado
    if filtro_limite and filtro_limite > 0:
        inscricoes = inscricoes[:filtro_limite]


    # Gerar PDF
    buffer = gerar_pdf_inscricoes_detalhado(inscricoes)

    filename = f"inscricoes_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


def gerar_pdf_inscricoes_detalhado(inscricoes):
    """Gera PDF detalhado com as inscrições filtradas"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()

    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor("#724d99"),
        spaceAfter=20,
        alignment=1  # Center
    )

    elements.append(Paragraph("CFA Brasil - Comissão Feminina de Automobilismo - Relatório de Inscrições", title_style))
    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"Total de inscrições: {len(inscricoes)}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))

    # Tabela
    data = [['Nome', 'Email', 'Telefone', 'UF', 'Programa', 'Ano', 'Status', 'Data']]

    for ins in inscricoes:
        status_map = {
            'pendente': 'Pendente',
            'pre_selecionada': 'Pré-Sel.',
            'backup': 'Backup',
            'selecionada': 'Selecionada',
            'nao_selecionada': 'Não Sel.'
        }

        data.append([
            ins.nome[:25],
            ins.email[:30],
            ins.telefone,
            ins.estado,
            ins.programa.nome[:20],
            str(ins.ano_inscricao),
            status_map.get(ins.status, ins.status),
            ins.criado_em.strftime('%d/%m/%Y')
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/admin/inscricao/<int:inscricao_id>/status', methods=['POST'])
def admin_update_status(inscricao_id):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    nova = request.form.get('status')
    if nova not in ['pendente', 'selecionada', 'nao_selecionada', 'pre_selecionada', 'backup']:
        flash('Status inválido.', 'danger')
        return redirect(url_for('admin_dashboard'))

    ins = Inscricao.query.get_or_404(inscricao_id)
    status_anterior = ins.status
    ins.status = nova
    db.session.commit()

    # Enviar email de seleção se mudou para "selecionada" e é do programa Imersão
      # Enviar emails de seleção se mudou para "selecionada" e é do programa Imersão
    if nova == 'selecionada' and status_anterior != 'selecionada' and ins.programa.slug == 'imersao':
        enviados, erros = enviar_email_selecao(ins)
        if enviados > 0:
            flash(f'Status atualizado! {enviados} email(s) de palestra enviado(s).', 'success')
            if erros > 0:
                flash(f'⚠ {erros} email(s) não puderam ser enviados.', 'warning')
        elif erros > 0:
            flash('Status atualizado, mas houve erro ao enviar emails de seleção.', 'warning')
        else:
            flash('Status atualizado, mas nenhuma palestra selecionada.', 'warning')
    else:
        flash('Status atualizado com sucesso.', 'success')


    return redirect(url_for('admin_dashboard'))



@app.route('/admin/inscricao/<int:inscricao_id>/certificados/enviar', methods=['POST'])
def admin_enviar_certificados(inscricao_id):
    """Envia certificados por email para uma candidata"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    inscricao = Inscricao.query.get_or_404(inscricao_id)

    if inscricao.programa.slug != 'imersao':
        flash('Certificados disponíveis apenas para o programa Imersão.', 'warning')
        return redirect(url_for('admin_dashboard'))

    sucesso, mensagem = enviar_certificados_email(inscricao)

    if sucesso:
        inscricao.certificado_enviado = True
        db.session.commit()
        flash(f'Certificados enviados para {inscricao.email}!', 'success')
    else:
        flash(f'Erro ao enviar certificados: {mensagem}', 'danger')

    return redirect(url_for('admin_dashboard'))


# ✅ NOVA ROTA: Ver histórico completo de uma candidata
@app.route('/admin/historico/<email>')
def admin_historico_candidata(email):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    historico = obter_historico_inscricoes(email)
    if not historico:
        flash('Nenhuma inscrição encontrada para este email.', 'warning')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_historico.html', historico=historico, email=email)

@app.route('/admin/update-status-em-massa', methods=['POST'])
def admin_update_status_em_massa():
    """Atualiza status de múltiplas inscrições de uma vez"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    novo_status = request.form.get('novo_status')
    inscricoes_ids = request.form.getlist('inscricoes_ids')
    palestra_filtrada = request.form.get('palestra_filtrada')  # NOVO: receber palestra filtrada

    status_map = {
        'pendente': 'pendente',
        'selecionada': 'selecionada',
        'nao_selecionada': 'nao_selecionada',  # AQUI
        'pre_selecionada': 'pre_selecionada',   # AQUI
        'backup': 'backup'
    }

    if novo_status not in status_map.values():
        flash('Status inválido.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if not inscricoes_ids:
        flash('Nenhuma inscrição foi selecionada.', 'warning')
        return redirect(url_for('admin_dashboard'))

    count = 0
    emails_enviados = 0

    for inscricao_id in inscricoes_ids:
        try:
            ins = Inscricao.query.get(int(inscricao_id))
            if not ins:
                continue

            status_anterior = ins.status
            ins.status = status_map[novo_status]



            # NOVO: Se está selecionando E tem filtro de palestra específica
            if novo_status == 'selecionada' and palestra_filtrada and ins.programa.slug == 'imersao':
                # NOVO: Se está selecionando E tem filtro de palestra especifica
                if not ins.palestras_selecionadas:
                    ins.palestras_selecionadas = []

                # Adicionar palestra se ainda não estiver na lista
                palestra_norm = palestra_filtrada.replace('_', '')
                palestra_ja_estava = palestra_norm in ins.palestras_selecionadas

                if not palestra_ja_estava:
                    ins.palestras_selecionadas.append(palestra_norm)
                    flag_modified(ins, 'palestras_selecionadas')



                if status_anterior != 'selecionada' or not palestra_ja_estava:
                    enviados, erros = enviar_email_selecao(ins, palestras_especificas=[palestra_norm])
                    emails_enviados += enviados

            # Se está selecionando SEM filtro de palestra (todas)
            elif novo_status == 'selecionada' and not palestra_filtrada and ins.programa.slug == 'imersao':
                # Selecionar para TODAS as palestras que ela se inscreveu
                if ins.campos_extras and 'palestras_selecionadas' in ins.campos_extras:
                    palestras_inscricao = ins.campos_extras['palestras_selecionadas']
                    ins.palestras_selecionadas = [p.replace('_', '') for p in palestras_inscricao]

                elif status_anterior != 'selecionada':
                    enviados, erros = enviar_email_selecao(ins, palestras_especificas=[palestra_norm])
                    emails_enviados += enviados

            count += 1

        except:
            continue

    db.session.commit()

    flash(f'{count} inscrições atualizadas com sucesso!', 'success')
    if emails_enviados > 0:
        flash(f'{emails_enviados} emails de seleção enviados!', 'info')

    return redirect(url_for('admin_dashboard') + '?' + request.query_string.decode())


@app.route('/admin/enviar-certificados-em-massa', methods=['POST'])
def admin_enviar_certificados_em_massa():
    """Envia certificados para múltiplas inscrições de uma vez"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    inscricoes_ids = request.form.getlist('inscricoes_ids[]')

    if not inscricoes_ids:
        flash('Nenhuma inscrição foi selecionada.', 'warning')
        return redirect(url_for('admin_dashboard'))

    # Processar envio de certificados
    sucessos = 0
    erros = 0
    nao_elegiveis = 0

    for inscricao_id in inscricoes_ids:
        try:
            inscricao = Inscricao.query.get(int(inscricao_id))
            if not inscricao:
                continue

            # Verificar se é do programa Imersão
            if inscricao.programa.slug != 'imersao':
                nao_elegiveis += 1
                continue

            # Verificar se tem palestras selecionadas
            if not inscricao.campos_extras or 'palestras_selecionadas' not in inscricao.campos_extras:
                nao_elegiveis += 1
                continue

            if not inscricao.campos_extras['palestras_selecionadas']:
                nao_elegiveis += 1
                continue

            # Enviar certificados
            sucesso, mensagem = enviar_certificados_email(inscricao)

            if sucesso:
                sucessos += 1
            else:
                erros += 1

        except Exception as e:
            erros += 1
            continue

    # Mensagens de feedback
    if sucessos > 0:
        flash(f'✓ {sucessos} certificado(s) enviado(s) com sucesso!', 'success')
    if erros > 0:
        flash(f'✗ {erros} erro(s) ao enviar certificados.', 'danger')
    if nao_elegiveis > 0:
        flash(f'⚠ {nao_elegiveis} inscrição(ões) não elegível(is) para certificados (apenas Imersão com palestras selecionadas).', 'warning')

    return redirect(url_for('admin_dashboard') + '?' + request.query_string.decode())

@app.route('/admin/inscricao/<int:inscricao_id>/presenca', methods=['POST'])
def admin_atualizar_presenca(inscricao_id):
    """Atualiza presença nas palestras - APENAS Imersão + Selecionada"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    inscricao = Inscricao.query.get_or_404(inscricao_id)

    # VERIFICAR: Apenas Imersão + Selecionada
    if inscricao.programa.slug != 'imersao' or inscricao.status != 'selecionada':
        flash('Presença só pode ser registrada para candidatas selecionadas na Imersão.', 'warning')
        return redirect(url_for('admin_dashboard'))

    # Inicializar dicionário de presença
    presenca = {}

    # Pegar todas as palestras marcadas
    for key in request.form:
        if key.startswith('presenca_'):
            palestra_id = key.replace('presenca_', '')
            presenca[palestra_id] = True

    # Salvar no banco
    inscricao.presenca_palestras = presenca
    db.session.commit()

    flash(f'Presenças atualizadas para {inscricao.nome}!', 'success')
    return redirect(url_for('admin_dashboard') + '?' + request.query_string.decode())

@app.route('/presenca/<int:palestra_numero>/<token>')
def presenca_palestra(palestra_numero, token):
    """Página pública para candidatas confirmarem presença"""

    # Verificar se a palestra existe
    palestra_id = f'palestra{palestra_numero}'
    if palestra_id not in PALESTRAS_IMERSAO:
        flash('Palestra não encontrada.', 'danger')
        return redirect(url_for('index'))

    palestra = PALESTRAS_IMERSAO[palestra_id]

    # Verificar token simples (você pode melhorar isso)
    if token != f"cfa2026palestra{palestra_numero}":
        flash('Link inválido ou expirado.', 'danger')
        return redirect(url_for('index'))

    return render_template('presenca.html',
                         palestra=palestra,
                         palestra_id=palestra_id,
                         palestranumero=palestra_numero,
                         token=token)




@app.route('/presenca/<int:palestranumero>/<token>/confirmar', methods=['POST'])
def confirmar_presenca(palestranumero, token):
    if token != f'cfa2026palestra{palestranumero}':
        return jsonify({'success': False, 'message': 'Link inválido'}, 403)

    email = request.form.get('email', '').strip().lower()
    if not email:
        return jsonify({'success': False, 'message': 'Email obrigatório'}, 400)

    palestra_id = f'palestra{palestranumero}'

    inscricao = Inscricao.query.filter(
        Inscricao.email == email,
        Inscricao.programa.has(slug='imersao'),
        Inscricao.status == 'selecionada'
    ).first()

    if not inscricao:
        return jsonify({'success': False, 'message': 'Email não encontrado ou você não foi selecionada.'}, 404)

    if not inscricao.palestras_selecionadas or palestra_id not in inscricao.palestras_selecionadas:
        return jsonify({'success': False, 'message': 'Você não foi selecionada para esta palestra.'}, 403)

    # CORREÇÃO: Inicializar e marcar como modificado
    if not inscricao.presenca_palestras:
        inscricao.presenca_palestras = {}

    inscricao.presenca_palestras[palestra_id] = True
    flag_modified(inscricao, 'presenca_palestras')  # ← ADICIONAR ESTA LINHA

    db.session.commit()

    return jsonify({'success': True, 'message': f'Presença confirmada com sucesso, {inscricao.nome}!'})

@app.route('/admin/config', methods=['GET', 'POST'])
def admin_config():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    programas = Programa.query.order_by(Programa.nome).all()
    config_email = ConfiguracaoEmail.query.first()
    if not config_email:
        config_email = ConfiguracaoEmail()
        db.session.add(config_email)
        db.session.commit()

    if request.method == 'POST':
    # Templates de confirmação
        template_assunto = request.form.get('template_assunto', '').strip()
        template_corpo = request.form.get('template_corpo', '').strip()

        # Templates de seleção
        template_selecao_assunto = request.form.get('template_selecao_assunto', '').strip()
        template_selecao_corpo = request.form.get('template_selecao_corpo', '').strip()
        link_zoom = request.form.get('link_zoom', '').strip()

        if template_assunto:
            config_email.template_assunto = template_assunto
        if template_corpo:
            config_email.template_corpo = template_corpo
        if template_selecao_assunto:
            config_email.template_selecao_assunto = template_selecao_assunto
        if template_selecao_corpo:
            config_email.template_selecao_corpo = template_selecao_corpo
        if link_zoom:
            config_email.link_zoom = link_zoom

                # Templates de seleção
        template_selecao_assunto = request.form.get('template_selecao_assunto', '').strip()
        template_selecao_corpo = request.form.get('template_selecao_corpo', '').strip()

        # Salvar links do Zoom das palestras no dicionário
        for i in range(1, 6):
            link_key = f'link_zoom_palestra{i}'
            link_value = request.form.get(link_key, '').strip()
            if link_value:
                PALESTRAS_IMERSAO[f'palestra{i}']['link_zoom'] = link_value



        for programa in programas:
            prefix = f'programa_{programa.id}_'
            data_abertura_str = request.form.get(prefix + 'data_abertura')
            data_fechamento_str = request.form.get(prefix + 'data_fechamento')
            ativo_str = request.form.get(prefix + 'ativo')

            if data_abertura_str:
                try:
                    programa.data_abertura = datetime.strptime(data_abertura_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            else:
                programa.data_abertura = None

            if data_fechamento_str:
                try:
                    programa.data_fechamento = datetime.strptime(data_fechamento_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            else:
                programa.data_fechamento = None

            programa.ativo = (ativo_str == 'on')

            descricao_curta = request.form.get(prefix + 'descricao_curta', '').strip()
            descricao = request.form.get(prefix + 'descricao', '').strip()
            programa.descricao_curta = descricao_curta
            programa.descricao = descricao

        db.session.commit()
        flash('Configurações atualizadas com sucesso.', 'success')
        return redirect(url_for('admin_config'))

    avisos = Aviso.query.order_by(Aviso.criado_em.desc()).all()
    return render_template('admin_config.html', programas=programas, config_email=config_email, avisos=avisos, palestras_imersao=PALESTRAS_IMERSAO)

@app.route('/admin/avisos/novo', methods=['POST'])
def admin_novo_aviso():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    programa_id = request.form.get('programa_id')
    titulo = request.form.get('titulo', '').strip()
    descricao = request.form.get('descricao', '').strip()
    if not programa_id or not programa_id.isdigit():
        flash('Programa inválido.', 'danger')
        return redirect(url_for('admin_config'))
    if not titulo or not descricao:
        flash('Título e descrição do aviso são obrigatórios.', 'danger')
        return redirect(url_for('admin_config'))
    aviso = Aviso(programa_id=int(programa_id), titulo=titulo, descricao=descricao, ativo=True)
    db.session.add(aviso)
    db.session.commit()
    flash('Aviso criado com sucesso.', 'success')
    return redirect(url_for('admin_config'))

@app.route('/admin/avisos/<int:aviso_id>/toggle', methods=['POST'])
def admin_toggle_aviso(aviso_id):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    aviso = Aviso.query.get_or_404(aviso_id)
    aviso.ativo = not aviso.ativo
    db.session.commit()
    flash('Aviso atualizado com sucesso.', 'success')
    return redirect(url_for('admin_config'))


def calcular_idade(data_nascimento_str):
    """Calcula idade a partir de string de data"""
    try:
        if isinstance(data_nascimento_str, str):
            data_nasc = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
        else:
            data_nasc = data_nascimento_str
        hoje = date.today()
        idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
        return idade
    except:
        return None

def obter_regiao(uf):
    """Retorna a região do Brasil baseada no estado"""
    regioes = {
        'Norte': ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
        'Nordeste': ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
        'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
        'Sudeste': ['ES', 'MG', 'RJ', 'SP'],
        'Sul': ['PR', 'RS', 'SC']
    }
    for regiao, estados in regioes.items():
        if uf.upper() in estados:
            return regiao
    return 'Não identificado'

def gerar_estatisticas_completas():
    """Gera todas as estatísticas do sistema"""

    inscricoes = Inscricao.query.all()
    total = len(inscricoes)

    if total == 0:
        return None

    stats = {
        'total_geral': total,
        'por_ano': {},
        'por_programa': {},
        'por_status': {},
        'por_regiao': {},
        'por_estado': {},
        'por_cor': {},
        'por_faixa_etaria': {},
        'por_escolaridade': {},
        'por_identidade_genero': {},
        'candidatas_recorrentes': 0,
        'taxa_selecao': 0,
        'idades': [],
        'anos_disponiveis': []
    }

    # Contadores
    emails_unicos = set()
    emails_multiplos = set()

    for ins in inscricoes:
        # Anos
        ano = ins.ano_inscricao
        stats['por_ano'][ano] = stats['por_ano'].get(ano, 0) + 1
        if ano not in stats['anos_disponiveis']:
            stats['anos_disponiveis'].append(ano)

        # Programas
        programa = ins.programa.nome
        stats['por_programa'][programa] = stats['por_programa'].get(programa, 0) + 1

        # Status
        status_map = {
            'pendente': 'Pendente',
            'pre_selecionada': 'Pré-Selecionada',
            'backup': 'Backup',
            'selecionada': 'Selecionada',
            'nao_selecionada': 'Não Selecionada'
        }
        status = status_map.get(ins.status, ins.status)
        stats['por_status'][status] = stats['por_status'].get(status, 0) + 1

        # Região e Estado
        regiao = obter_regiao(ins.estado)
        stats['por_regiao'][regiao] = stats['por_regiao'].get(regiao, 0) + 1
        stats['por_estado'][ins.estado] = stats['por_estado'].get(ins.estado, 0) + 1

        # Candidatas recorrentes
        if ins.email in emails_unicos:
            emails_multiplos.add(ins.email)
        emails_unicos.add(ins.email)

        # Campos extras (JSON)
        if ins.campos_extras:
            # Cor/Raça
            cor = ins.campos_extras.get('cor')
            if cor:
                stats['por_cor'][cor] = stats['por_cor'].get(cor, 0) + 1

            # Idade
            data_nasc = ins.campos_extras.get('data_nascimento')
            if data_nasc:
                idade = calcular_idade(data_nasc)
                if idade:
                    stats['idades'].append(idade)
                    # Faixas etárias
                    if idade < 15:
                        faixa = 'Até 14 anos'
                    elif idade <= 17:
                        faixa = '15-17 anos'
                    elif idade <= 22:
                        faixa = '18-22 anos'
                    elif idade <= 29:
                        faixa = '23-29 anos'
                    elif idade <= 39:
                        faixa = '30-39 anos'
                    else:
                        faixa = '40+ anos'
                    stats['por_faixa_etaria'][faixa] = stats['por_faixa_etaria'].get(faixa, 0) + 1

            # Idade (e-sports)
            idade_direta = ins.campos_extras.get('idade')
            if idade_direta and not data_nasc:
                try:
                    idade = int(idade_direta)
                    stats['idades'].append(idade)
                    if idade < 15:
                        faixa = 'Até 14 anos'
                    elif idade <= 17:
                        faixa = '15-17 anos'
                    elif idade <= 22:
                        faixa = '18-22 anos'
                    elif idade <= 29:
                        faixa = '23-29 anos'
                    elif idade <= 39:
                        faixa = '30-39 anos'
                    else:
                        faixa = '40+ anos'
                    stats['por_faixa_etaria'][faixa] = stats['por_faixa_etaria'].get(faixa, 0) + 1
                except:
                    pass

            # Escolaridade
            escolaridade = ins.campos_extras.get('escolaridade')
            if escolaridade:
                stats['por_escolaridade'][escolaridade] = stats['por_escolaridade'].get(escolaridade, 0) + 1

            # Identidade de gênero
            identidade = ins.campos_extras.get('identidade_genero')
            if identidade:
                stats['por_identidade_genero'][identidade] = stats['por_identidade_genero'].get(identidade, 0) + 1

    # Cálculos finais
    stats['candidatas_recorrentes'] = len(emails_multiplos)
    stats['candidatas_unicas'] = len(emails_unicos)

    selecionadas = stats['por_status'].get('Selecionada', 0)
    stats['taxa_selecao'] = round((selecionadas / total) * 100, 2) if total > 0 else 0

    # Ordenar
    stats['anos_disponiveis'].sort(reverse=True)
    stats['por_ano'] = dict(sorted(stats['por_ano'].items(), reverse=True))
    stats['por_regiao'] = dict(sorted(stats['por_regiao'].items(), key=lambda x: x[1], reverse=True))
    stats['por_estado'] = dict(sorted(stats['por_estado'].items(), key=lambda x: x[1], reverse=True))
    stats['por_programa'] = dict(sorted(stats['por_programa'].items(), key=lambda x: x[1], reverse=True))

    return stats


def gerar_pdf_dashboard_estatisticas():
    """Gera PDF profissional com dashboard completo de estatísticas"""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buffer = BytesIO()

    # Documento em paisagem para melhor visualização
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )

    elements = []
    styles = getSampleStyleSheet()

    # Estilos customizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#E10600'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#E10600'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT
    )

    # Obter estatísticas
    stats = gerar_estatisticas_completas()

    if not stats:
        elements.append(Paragraph("Nenhuma inscrição encontrada no sistema.", normal_style))
        doc.build(elements)
        buffer.seek(0)
        return buffer

    # === PÁGINA 1: RESUMO EXECUTIVO ===
    elements.append(Paragraph("CFA BRASIL - COMISSÃO FEMININA DE AUTOMOBILISMO", title_style))
    elements.append(Paragraph("Dashboard Estatístico Completo", subtitle_style))
    elements.append(Paragraph(
        f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        normal_style
    ))
    elements.append(Spacer(1, 0.3*inch))

    # Resumo Executivo
    elements.append(Paragraph("RESUMO EXECUTIVO", subtitle_style))

    resumo_data = [
        ['Métrica', 'Valor'],
        ['Total de Inscrições', str(stats['total_geral'])],
        ['Candidatas Únicas', str(stats['candidatas_unicas'])],
        ['Candidatas Recorrentes', f"{stats['candidatas_recorrentes']} ({round(stats['candidatas_recorrentes']/stats['candidatas_unicas']*100, 1)}%)"],
        ['Taxa de Seleção Geral', f"{stats['taxa_selecao']}%"],
        ['Anos com Inscrições', ', '.join(map(str, stats['anos_disponiveis']))],
        ['Programas Ativos', str(len(stats['por_programa']))]
    ]

    resumo_table = Table(resumo_data, colWidths=[3*inch, 2*inch])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(resumo_table)
    elements.append(Spacer(1, 0.3*inch))

    # Distribuição por Status
    elements.append(Paragraph("Distribuição por Status", subtitle_style))
    status_data = [['Status', 'Quantidade', 'Percentual']]
    for status, qtd in stats['por_status'].items():
        perc = round((qtd / stats['total_geral']) * 100, 1)
        status_data.append([status, str(qtd), f"{perc}%"])

    status_table = Table(status_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(status_table)

    elements.append(PageBreak())

    # === PÁGINA 2: DISTRIBUIÇÃO POR PROGRAMA E ANO ===
    elements.append(Paragraph("DISTRIBUIÇÃO POR PROGRAMA", subtitle_style))

    programa_data = [['Programa', 'Inscrições', '% do Total']]
    for programa, qtd in stats['por_programa'].items():
        perc = round((qtd / stats['total_geral']) * 100, 1)
        programa_data.append([programa[:40], str(qtd), f"{perc}%"])

    programa_table = Table(programa_data, colWidths=[3.5*inch, 1.5*inch, 1.5*inch])
    programa_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(programa_table)
    elements.append(Spacer(1, 0.3*inch))

    # Distribuição por Ano
    elements.append(Paragraph("DISTRIBUIÇÃO POR ANO", subtitle_style))

    ano_data = [['Ano', 'Inscrições', '% do Total']]
    for ano, qtd in stats['por_ano'].items():
        perc = round((qtd / stats['total_geral']) * 100, 1)
        ano_data.append([str(ano), str(qtd), f"{perc}%"])

    ano_table = Table(ano_data, colWidths=[2*inch, 2*inch, 2*inch])
    ano_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(ano_table)

    elements.append(PageBreak())

    # === PÁGINA 3: DISTRIBUIÇÃO GEOGRÁFICA ===
    elements.append(Paragraph("DISTRIBUIÇÃO GEOGRÁFICA", subtitle_style))

    # Por Região
    elements.append(Paragraph("Por Região do Brasil", normal_style))
    elements.append(Spacer(1, 0.1*inch))

    regiao_data = [['Região', 'Inscrições', '% do Total']]
    for regiao, qtd in stats['por_regiao'].items():
        perc = round((qtd / stats['total_geral']) * 100, 1)
        regiao_data.append([regiao, str(qtd), f"{perc}%"])

    regiao_table = Table(regiao_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    regiao_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(regiao_table)
    elements.append(Spacer(1, 0.3*inch))

    # Por Estado (Top 10)
    elements.append(Paragraph("Top 10 Estados", normal_style))
    elements.append(Spacer(1, 0.1*inch))

    estado_data = [['UF', 'Inscrições', '% do Total']]
    top_estados = list(stats['por_estado'].items())[:10]
    for estado, qtd in top_estados:
        perc = round((qtd / stats['total_geral']) * 100, 1)
        estado_data.append([estado, str(qtd), f"{perc}%"])

    estado_table = Table(estado_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
    estado_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(estado_table)

    elements.append(PageBreak())

    # === PÁGINA 4: DADOS DEMOGRÁFICOS ===
    elements.append(Paragraph("DADOS DEMOGRÁFICOS", subtitle_style))

    # Faixa Etária
    if stats['por_faixa_etaria']:
        elements.append(Paragraph("Distribuição por Faixa Etária", normal_style))
        elements.append(Spacer(1, 0.1*inch))

        # Ordenar faixas etárias logicamente
        ordem_faixas = ['Até 14 anos', '15-17 anos', '18-22 anos', '23-29 anos', '30-39 anos', '40+ anos']
        faixa_data = [['Faixa Etária', 'Quantidade', '% do Total']]

        total_com_idade = sum(stats['por_faixa_etaria'].values())
        for faixa in ordem_faixas:
            if faixa in stats['por_faixa_etaria']:
                qtd = stats['por_faixa_etaria'][faixa]
                perc = round((qtd / total_com_idade) * 100, 1)
                faixa_data.append([faixa, str(qtd), f"{perc}%"])

        faixa_table = Table(faixa_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        faixa_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(faixa_table)

        if stats['idades']:
            idade_media = round(sum(stats['idades']) / len(stats['idades']), 1)
            idade_min = min(stats['idades'])
            idade_max = max(stats['idades'])
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(
                f"Idade Média: {idade_media} anos | Mínima: {idade_min} anos | Máxima: {idade_max} anos",
                normal_style
            ))

        elements.append(Spacer(1, 0.3*inch))

    # Raça/Cor
    if stats['por_cor']:
        elements.append(Paragraph("Autodeclaração de Raça/Cor", normal_style))
        elements.append(Spacer(1, 0.1*inch))

        cor_data = [['Raça/Cor', 'Quantidade', '% do Total']]
        total_com_cor = sum(stats['por_cor'].values())
        for cor, qtd in sorted(stats['por_cor'].items(), key=lambda x: x[1], reverse=True):
            perc = round((qtd / total_com_cor) * 100, 1)
            cor_data.append([cor, str(qtd), f"{perc}%"])

        cor_table = Table(cor_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        cor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(cor_table)
        elements.append(Spacer(1, 0.3*inch))

    # Identidade de Gênero
    if stats['por_identidade_genero']:
        elements.append(Paragraph("Identidade de Gênero", normal_style))
        elements.append(Spacer(1, 0.1*inch))

        genero_data = [['Identidade', 'Quantidade', '% do Total']]
        total_genero = sum(stats['por_identidade_genero'].values())
        for genero, qtd in sorted(stats['por_identidade_genero'].items(), key=lambda x: x[1], reverse=True):
            perc = round((qtd / total_genero) * 100, 1)
            genero_data.append([genero, str(qtd), f"{perc}%"])

        genero_table = Table(genero_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        genero_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(genero_table)
        elements.append(Spacer(1, 0.3*inch))

    # Escolaridade
    if stats['por_escolaridade']:
        elements.append(Paragraph("Escolaridade", normal_style))
        elements.append(Spacer(1, 0.1*inch))

        escolaridade_data = [['Nível', 'Quantidade', '% do Total']]
        total_escolaridade = sum(stats['por_escolaridade'].values())
        for nivel, qtd in sorted(stats['por_escolaridade'].items(), key=lambda x: x[1], reverse=True):
            perc = round((qtd / total_escolaridade) * 100, 1)
            escolaridade_data.append([nivel[:35], str(qtd), f"{perc}%"])

        escolaridade_table = Table(escolaridade_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        escolaridade_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E10600')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(escolaridade_table)

    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/admin/estatisticas')
def admin_estatisticas():
    """Página de visualização de estatísticas"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    stats = gerar_estatisticas_completas()

    if not stats:
        flash('Não há dados suficientes para gerar estatísticas.', 'warning')
        return redirect(url_for('admin_dashboard'))

    # Preparar dados para o template (top 10 estados)
    stats['top_estados'] = list(stats['por_estado'].items())[:10]

    return render_template('admin_estatisticas.html', stats=stats)


@app.route('/admin/exportar-estatisticas-pdf')
def admin_exportar_estatisticas_pdf():
    """Exporta dashboard de estatísticas em PDF"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    buffer = gerar_pdf_dashboard_estatisticas()
    filename = f"dashboard_estatistico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


# CLI
@app.cli.command('init-db')
def init_db_command():
    """Inicializa o banco de dados."""
    with app.app_context():
        db.create_all()
        if not AdminUser.query.first():
            email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
            senha = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin = AdminUser(email=email, password_hash=generate_password_hash(senha))
            db.session.add(admin)
            print(f'✅ Admin criado: {email}')

        programas_padrao = [
            ('Estágio Motorsport', 'estagio-motorsport'),
            ('Imersão para Mulheres no Motorsport', 'imersao'),
            ('Seletiva de Kart CFA Brasil', 'kart'),
            ('Campeonato de E-Sports CFA Brasil', 'e-sports'),
            ('FIA Girls on Track - Experiência WEC', 'experiencia-wec'),
        ]
        for nome, slug in programas_padrao:
            if not Programa.query.filter_by(slug=slug).first():
                p = Programa(nome=nome, slug=slug, descricao=f'Descrição para {nome}.', ativo=True)
                db.session.add(p)
                print(f'✅ Programa criado: {nome}')

        if not ConfiguracaoEmail.query.first():
            db.session.add(ConfiguracaoEmail())

        db.session.commit()
        print('✅ Banco de dados inicializado!')



def enviar_lembretes_palestras_do_dia():
    """
    Envia lembretes para todas as candidatas selecionadas
    cujas palestras acontecem hoje.
    Retorna (total_enviados, total_erros)
    """
    from datetime import date

    hoje = date.today()
    hoje_str = hoje.strftime('%d/%m/%Y')

    print(f"\n{'='*60}")
    print(f"🔔 INICIANDO ENVIO DE LEMBRETES - {hoje_str}")
    print(f"{'='*60}\n")

    # Buscar todas as candidatas selecionadas do programa Imersão
    inscricoes = Inscricao.query.join(Programa).filter(
        Inscricao.status == 'selecionada',
        Programa.slug == 'imersao'
    ).all()

    print(f"📊 Total de candidatas selecionadas: {len(inscricoes)}")

    config = ConfiguracaoEmail.query.first()
    if not config:
        print("❌ Configuração de email não encontrada")
        return 0, 0  # ✅ CORRIGIDO

    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT', '587')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    smtp_from = f"CFA Brasil <{smtp_user}>"

    if not (smtp_host and smtp_user and smtp_pass):
        print('❌ SMTP não configurado')
        return 0, 0  # ✅ CORRIGIDO

    total_enviados = 0
    total_erros = 0

    # Verificar quais palestras acontecem hoje
    palestras_hoje = []
    for palestra_id, palestra in PALESTRAS_IMERSAO.items():
        if palestra['data'] == hoje_str:
            palestras_hoje.append((palestra_id, palestra))
            print(f"📅 Palestra de hoje: {palestra['titulo']} às {palestra['horario']}")

    if not palestras_hoje:
        print(f"ℹ️ Nenhuma palestra agendada para hoje ({hoje_str})")
        return 0, 0  # ✅ CORRIGIDO

    print(f"\n📧 Iniciando envio de lembretes...\n")

    # Para cada candidata
    for inscricao in inscricoes:
        if not inscricao.campos_extras or 'palestras_selecionadas' not in inscricao.campos_extras:
            continue

        palestras_candidata = inscricao.campos_extras['palestras_selecionadas']
        palestras_candidata_norm = [p.replace('_', '') for p in palestras_candidata]

        # Verificar se ela está inscrita em alguma palestra de hoje
        for palestra_id, palestra in palestras_hoje:
            if palestra_id in palestras_candidata_norm or f'palestra_{palestra_id[-1]}' in palestras_candidata:
                # Montar email de lembrete
                assunto = f"🔔 Lembrete: Palestra hoje às {palestra['horario']}"

                corpo = f"""Olá {inscricao.nome},

Este é um lembrete de que você tem uma palestra HOJE! 🎉

📌 {palestra['titulo']}
📅 Hoje, {palestra['data']}
🕐 Horário: {palestra['horario']}
⏱️ Duração: {palestra['carga_horaria']}
👩‍🏫 Palestrante(s): {', '.join(palestra['palestrantes'])}

🔗 Link da sala Zoom: {palestra.get('link_zoom', '[Link não configurado]')}

Não se atrase! Nos vemos lá! 😊

Comissão Feminina de Automobilismo - CFA Brasil"""

                msg = EmailMessage()
                msg['Subject'] = assunto
                msg['From'] = smtp_from
                msg['To'] = inscricao.email
                msg.set_content(corpo)

                try:
                    with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_pass)
                        server.send_message(msg)
                    total_enviados += 1
                    print(f"✅ Lembrete enviado: {inscricao.nome} ({inscricao.email}) - {palestra['titulo']}")
                except Exception as e:
                    total_erros += 1
                    print(f"❌ Erro ao enviar para {inscricao.email}: {e}")

    print(f"\n{'='*60}")
    print(f"📊 RESUMO DO ENVIO DE LEMBRETES")
    print(f"{'='*60}")
    print(f"✅ Enviados com sucesso: {total_enviados}")
    print(f"❌ Erros: {total_erros}")
    print(f"{'='*60}\n")

    return total_enviados, total_erros  # ✅ Sempre retorna tupla


@app.route('/admin/enviar-lembretes-hoje', methods=['POST'])
def admin_enviar_lembretes_hoje():
    """Envia lembretes manualmente via dashboard"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    enviados, erros = enviar_lembretes_palestras_do_dia()

    if enviados > 0:
        flash(f'✅ {enviados} lembrete(s) enviado(s) com sucesso!', 'success')
    if erros > 0:
        flash(f'❌ {erros} erro(s) ao enviar lembretes.', 'danger')
    if enviados == 0 and erros == 0:
        flash('ℹ️ Nenhuma palestra agendada para hoje.', 'info')

    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)
