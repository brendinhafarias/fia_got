import os
import re
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_file
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from email.message import EmailMessage
import smtplib
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# CONFIGURAÇÃO BÁSICA
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload de arquivos
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

db = SQLAlchemy(app)

# Context processor para ano dinâmico
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# MODELOS
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
    
    # Campos específicos armazenados em JSON
    campos_extras = db.Column(db.JSON, nullable=True)
    
    # Arquivos
    foto_filename = db.Column(db.String(255), nullable=True)
    curriculo_filename = db.Column(db.String(255), nullable=True)
    
    # Relacionamentos
    programa_id = db.Column(db.Integer, db.ForeignKey('programas.id'), nullable=False)
    status = db.Column(db.String(20), default='pendente', nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ConfiguracaoEmail(db.Model):
    __tablename__ = 'configuracao_email'
    id = db.Column(db.Integer, primary_key=True)
    template_assunto = db.Column(db.String(255), nullable=False, default='Recebemos sua inscrição')
    template_corpo = db.Column(
        db.Text,
        nullable=False,
        default='Olá {nome},\n\nRecebemos sua inscrição para o programa {programa}.\n\nObrigada!\nEquipe FIA Girls on Track'
    )
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# FUNÇÕES AUXILIARES
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
    smtp_from = os.environ.get('SMTP_FROM', smtp_user)

    if not (smtp_host and smtp_user and smtp_pass):
        print('SMTP não configurado. Email não enviado.')
        print('Assunto:', assunto)
        print('Corpo:', corpo)
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

# ROTAS PÚBLICAS
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
    return render_template(
        'programa.html',
        programa=programa,
        avisos=avisos,
        aberto=aberto,
        hoje=hoje
    )

@app.route('/inscricao/<slug>', methods=['GET', 'POST'])
def inscricao(slug):
    programa = Programa.query.filter_by(slug=slug, ativo=True).first_or_404()
    hoje = date.today()
    
    if programa.data_abertura and hoje < programa.data_abertura:
        flash('Inscrições ainda não foram abertas para este programa.', 'warning')
        return redirect(url_for('programa_detalhe', slug=slug))
    if programa.data_fechamento and hoje > programa.data_fechamento:
        flash('Inscrições encerradas para este programa.', 'warning')
        return redirect(url_for('programa_detalhe', slug=slug))

    if request.method == 'POST':
        # Campos comuns
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        estado = request.form.get('estado', '').strip().upper()
        
        # Validações básicas
        erros = []
        if not nome:
            erros.append('Nome é obrigatório.')
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            erros.append('Email inválido.')
        if not telefone:
            erros.append('Telefone é obrigatório.')
        if not estado or len(estado) != 2:
            erros.append('Estado (UF) é obrigatório.')

        # Coletar campos específicos por programa
        campos_extras = {}
        
        if programa.slug == 'kart':
            campos_extras = processar_campos_kart(request.form, erros)
        elif programa.slug == 'imersao':
            campos_extras = processar_campos_imersao(request.form, erros)
        elif programa.slug == 'estagio-motorsport':
            campos_extras = processar_campos_estagio(request.form, erros)
        elif programa.slug == 'e-sports':
            campos_extras = processar_campos_esports(request.form, erros)

        # Upload de arquivos
        foto_filename = None
        curriculo_filename = None
        
        if programa.slug in ['kart', 'estagio-motorsport']:
            foto = request.files.get('foto')
            if foto and allowed_file(foto.filename, ['img']):
                original = secure_filename(foto.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
                foto_filename = f"{timestamp}_{original}"
                foto.save(os.path.join(app.config['UPLOAD_FOLDER'], foto_filename))
            elif programa.slug == 'kart' or programa.slug == 'estagio-motorsport':
                if not foto:
                    erros.append('Foto é obrigatória.')
        
        if programa.slug == 'estagio-motorsport':
            curriculo = request.files.get('curriculo')
            if curriculo and allowed_file(curriculo.filename, ['pdf']):
                original = secure_filename(curriculo.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
                curriculo_filename = f"{timestamp}_{original}"
                curriculo.save(os.path.join(app.config['UPLOAD_FOLDER'], curriculo_filename))

        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('inscricao.html', programa=programa)

        # Criar inscrição
        inscricao_obj = Inscricao(
            nome=nome,
            email=email,
            telefone=telefone,
            estado=estado,
            campos_extras=campos_extras,
            foto_filename=foto_filename,
            curriculo_filename=curriculo_filename,
            programa_id=programa.id,
            status='pendente'
        )
        
        db.session.add(inscricao_obj)
        db.session.commit()
        
        enviar_email_confirmacao(inscricao_obj)
        
        flash('Inscrição realizada com sucesso! Você receberá um email de confirmação.', 'success')
        return redirect(url_for('programa_detalhe', slug=slug))

    return render_template('inscricao.html', programa=programa)

def processar_campos_kart(form, erros):
    campos = {}
    
    # Data de nascimento
    data_nasc = form.get('data_nascimento', '').strip()
    if data_nasc:
        campos['data_nascimento'] = data_nasc
    else:
        erros.append('Data de nascimento é obrigatória.')
    
    # Autodeclaração de cor
    campos['cor'] = form.get('cor', '').strip()
    
    # Responsável (para menores)
    campos['nome_responsavel'] = form.get('nome_responsavel', '').strip()
    campos['telefone_responsavel'] = form.get('telefone_responsavel', '').strip()
    
    # Logística
    campos['tem_condicoes_logistica'] = form.get('tem_condicoes_logistica', '').strip()
    if not campos['tem_condicoes_logistica']:
        erros.append('Informe se tem condições de logística.')
    
    # Categoria
    campos['categoria'] = form.get('categoria', '').strip()
    if not campos['categoria']:
        erros.append('Selecione a categoria.')
    
    # Peso e altura
    campos['peso'] = form.get('peso', '').strip()
    campos['altura'] = form.get('altura', '').strip()
    
    # Vestuário
    campos['vestuario'] = form.getlist('vestuario')
    
    # Experiência
    campos['categoria_atual'] = form.get('categoria_atual', '').strip()
    campos['titulos_resultados'] = form.get('titulos_resultados', '').strip()
    
    # Autorização responsável (checkbox)
    campos['autorizacao_responsavel'] = form.get('autorizacao_responsavel') == 'on'
    
    return campos

def processar_campos_imersao(form, erros):
    campos = {}
    
    campos['cidade'] = form.get('cidade', '').strip()
    campos['escolaridade'] = form.get('escolaridade', '').strip()
    campos['participou_antes'] = form.get('participou_antes', '').strip()
    campos['como_ficou_sabendo'] = form.get('como_ficou_sabendo', '').strip()
    campos['modulo_interesse'] = form.get('modulo_interesse', '').strip()
    
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
    
    if not campos['concordo_compartilhamento']:
        erros.append('Você precisa concordar com o compartilhamento de dados.')
    
    return campos

def processar_campos_esports(form, erros):
    campos = {}
    
    campos['idade'] = form.get('idade', '').strip()
    campos['cidade'] = form.get('cidade', '').strip()
    campos['nickname'] = form.get('nickname', '').strip()
    campos['plataforma'] = form.get('plataforma', '').strip()
    campos['experiencia'] = form.get('experiencia', '').strip()
    
    return campos

# ROTAS ADMIN (mantidas as existentes)
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
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
    
    # Filtros
    programa_id = request.args.get('programa_id')
    nome = request.args.get('nome')
    status = request.args.get('status')
    estado = request.args.get('estado')
    
    if programa_id and programa_id.isdigit():
        query = query.filter(Inscricao.programa_id == int(programa_id))
    if nome:
        query = query.filter(Inscricao.nome.ilike(f'%{nome}%'))
    if status in ['pendente', 'selecionada', 'nao_selecionada', 'pre_selecionada']:
        query = query.filter(Inscricao.status == status)
    if estado:
        query = query.filter(Inscricao.estado == estado.upper())
    
    inscricoes = query.order_by(Inscricao.criado_em.desc()).all()
    
    # Estatísticas
    stats = {
        'pendentes': Inscricao.query.filter_by(status='pendente').count(),
        'pre_selecionadas': Inscricao.query.filter_by(status='pre_selecionada').count(),
        'selecionadas': Inscricao.query.filter_by(status='selecionada').count(),
        'nao_selecionadas': Inscricao.query.filter_by(status='nao_selecionada').count(),
        'total': Inscricao.query.count()
    }
    
    return render_template(
        'admin_dashboard.html',
        programas=programas,
        inscricoes=inscricoes,
        filtros=request.args,
        stats=stats,
        stats_geral=stats
    )

@app.route('/admin/inscricao/<int:inscricao_id>/status', methods=['POST'])
def admin_update_status(inscricao_id):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    nova = request.form.get('status')
    if nova not in ['pendente', 'selecionada', 'nao_selecionada', 'pre_selecionada']:
        flash('Status inválido.', 'danger')
        return redirect(url_for('admin_dashboard'))
    ins = Inscricao.query.get_or_404(inscricao_id)
    ins.status = nova
    db.session.commit()
    flash('Status atualizado com sucesso.', 'success')
    return redirect(url_for('admin_dashboard'))

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
        template_assunto = request.form.get('template_assunto', '').strip()
        template_corpo = request.form.get('template_corpo', '').strip()
        if template_assunto:
            config_email.template_assunto = template_assunto
        if template_corpo:
            config_email.template_corpo = template_corpo

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

        db.session.commit()
        flash('Configurações atualizadas com sucesso.', 'success')
        return redirect(url_for('admin_config'))

    avisos = Aviso.query.order_by(Aviso.criado_em.desc()).all()
    return render_template(
        'admin_config.html',
        programas=programas,
        config_email=config_email,
        avisos=avisos
    )

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
    aviso = Aviso(
        programa_id=int(programa_id),
        titulo=titulo,
        descricao=descricao,
        ativo=True
    )
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

# COMANDO CLI
@app.cli.command('init-db')
def init_db_command():
    """Inicializa o banco de dados."""
    with app.app_context():
        db.create_all()
        if not AdminUser.query.first():
            email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
            senha = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin = AdminUser(
                email=email,
                password_hash=generate_password_hash(senha)
            )
            db.session.add(admin)
            print(f'✅ Admin criado: {email}')

        programas_padrao = [
            ('Estágio Motorsport', 'estagio-motorsport'),
            ('Imersão para Mulheres no Motorsport', 'imersao'),
            ('Seletiva de Kart FIA Girls on Track Brasil', 'kart'),
            ('Campeonato de E-Sports FIA Girls on Track Brasil', 'e-sports')
        ]
        for nome, slug in programas_padrao:
            if not Programa.query.filter_by(slug=slug).first():
                p = Programa(
                    nome=nome,
                    slug=slug,
                    descricao=f'Descrição padrão para {nome}.',
                    ativo=True
                )
                db.session.add(p)
                print(f'✅ Programa criado: {nome}')

        if not ConfiguracaoEmail.query.first():
            db.session.add(ConfiguracaoEmail())

        db.session.commit()
        print('✅ Banco de dados inicializado!')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Para desenvolvimento local
    app.run(host='0.0.0.0', port=5000, debug=False)

