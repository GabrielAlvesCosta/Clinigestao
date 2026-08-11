import os
import socket
from flask import Flask, render_template, session, redirect, url_for, request
import sqlite3
from models.models import init_db, get_db, en, de
from controllers.controllers import api
from controllers.auth_controller import AuthController, CHAVE_CADASTRO_ATUAL
from models.usuario import Usuario

app = Flask(__name__, static_folder='static') 
app.secret_key = "chave_mestra_clinical_pep"


@app.context_processor
def inject_chave():
    return dict(CHAVE_CADASTRO_ATUAL=CHAVE_CADASTRO_ATUAL)

app.register_blueprint(api, url_prefix='/api')

@app.route("/")
def home():
    if "usuario" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    return AuthController.cadastro()

@app.route("/login", methods=["GET", "POST"])
def login():
    return AuthController.login()

@app.route("/logout")
def logout():
    return AuthController.logout()

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
        
    pacientes_descriptografados = []
    
    try:
        with get_db() as db:
            db.row_factory = sqlite3.Row
            pacientes_db = db.execute('SELECT * FROM pacientes ORDER BY id DESC').fetchall()
            
            for p in pacientes_db:
                p_dict = dict(p)
                p_dict['nome'] = de(p_dict.get('nome'))
                p_dict['dataNasc'] = de(p_dict.get('dataNasc'))
                p_dict['genero'] = de(p_dict.get('genero'))
                p_dict['documento'] = de(p_dict.get('documento'))
                p_dict['cartao'] = de(p_dict.get('cartao'))
                p_dict['contato'] = de(p_dict.get('contato'))
                pacientes_descriptografados.append(p_dict)
                
            pacientes_descriptografados = sorted(pacientes_descriptografados, key=lambda k: (k['nome'] or '').lower())
    except Exception as e:
        print(f"Erro ao carregar dashboard: {e}")
        
    return render_template("dashboard.html", usuario=session["usuario"], pacientes=pacientes_descriptografados)

@app.route("/adm")
def adm():
    if "usuario" not in session:
        return redirect(url_for("login"))
    if Usuario.normalizar_perfil(session["usuario"].get("admin", "nao")) == "admin":
        return redirect(url_for("usuarios"))
    return redirect(url_for("dashboard"))

@app.route("/usuarios")
def usuarios():
    if "usuario" not in session:
        return redirect(url_for("login"))
    
    if Usuario.normalizar_perfil(session["usuario"].get("admin", "nao")) != "admin":
        return redirect(url_for("dashboard"))
        
    return AuthController.usuarios()

@app.route("/usuarios/editar/<int:id>", methods=["POST"])
def editar_usuario(id):
    if "usuario" not in session:
        return redirect(url_for("login"))
    return AuthController.editar_usuario_post(id)

@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if "usuario" not in session:
        return redirect(url_for("login"))
        
    if request.method == "GET":
        return redirect(url_for("dashboard"))
        
    return AuthController.perfil()

@app.route("/cadastrar_paciente", methods=["POST"])
def cadastrar_paciente():
    if "usuario" not in session:
        return redirect(url_for("login"))
    
    nome = request.form.get("nome", "Sem Nome").strip()
    data_nasc_crua = request.form.get("data_nasc", "").strip() 
    
    data_nasc_formatada = "00/00/0000"
    if data_nasc_crua:
        partes_data = data_nasc_crua.split("-")
        if len(partes_data) == 3:
            data_nasc_formatada = f"{partes_data[2]}/{partes_data[1]}/{partes_data[0]}"
            
    genero = request.form.get("genero", "Não informado")
    documento = request.form.get("documento", "Não informado").strip()
    cartao = request.form.get("cartao", "Não informado").strip()
    contato = request.form.get("contato", "Não informado").strip()
    
    with get_db() as db:
        db.execute('''
            INSERT INTO pacientes (nome, dataNasc, genero, documento, cartao, contato)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            en(nome), 
            en(data_nasc_formatada), 
            en(genero), 
            en(documento), 
            en(cartao), 
            en(contato)
        ))
        db.commit()
    
    return redirect(url_for("dashboard"))

def get_available_port(start_port=5000):
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


if __name__ == '__main__':
    init_db()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", get_available_port()))
    app.run(debug=True, host=host, port=port, use_reloader=False)