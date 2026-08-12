import os
import time
import re
import secrets
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, session, flash
from models.models import de
from models.usuario import Usuario


CHAVE_CADASTRO_ATUAL = secrets.token_hex(4).upper()
print("="*40)
print(f"🔑 CHAVE DE CADASTRO GERADA: primeiro_cadastro?chave={CHAVE_CADASTRO_ATUAL}")
print("="*40)

class AuthController:

    @staticmethod
    def _processar_cadastro(template_name, redirect_para_login=False):
        if request.method == "POST":
            nome = request.form.get("nome", "").strip()
            email = request.form.get("email", "").strip()
            cargo = request.form.get("cargo", "").strip()
            crm_coren = (request.form.get("crm_coren") or request.form.get("crm_corem") or "").strip()
            senha = request.form.get("senha", "").strip()
            admin = Usuario.normalizar_perfil(request.form.get("admin", "nao"))

            if not re.search(r"[A-Z]", senha):
                return render_template(
                    template_name,
                    error="A senha precisa ter pelo menos 1 letra maiúscula (A-Z)",
                    nome=nome,
                    email=email,
                    cargo=cargo,
                    crm_coren=crm_coren,
                    admin=admin,
                )

            if not re.search(r"[a-z]", senha):
                return render_template(
                    template_name,
                    error="A senha precisa ter pelo menos 1 letra minúscula (a-z)",
                    nome=nome,
                    email=email,
                    cargo=cargo,
                    crm_coren=crm_coren,
                    admin=admin,
                )

            if not re.search(r"[^A-Za-z0-9]", senha):
                return render_template(
                    template_name,
                    error="A senha precisa ter pelo menos 1 caractere especial (!@#$)",
                    nome=nome,
                    email=email,
                    cargo=cargo,
                    crm_coren=crm_coren,
                    admin=admin,
                )

            if not nome or not email or not cargo or not senha:
                return render_template(template_name, error="Preencha os campos obrigatórios")

            if Usuario.email_existe(email):
                return render_template(template_name, error="Email já cadastrado")

            file = request.files.get("assinatura")
            assinatura_filename = ""
            if file and file.filename != "":
                filename = f"{int(time.time())}_{secure_filename(file.filename)}"
                upload_path = os.path.join("static", "uploads")
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                assinatura_filename = filename

            try:
                usuario = Usuario(nome, email, cargo, crm_coren, senha, admin, assinatura_filename)
                usuario.salvar()
            except ValueError as exc:
                return render_template(
                    template_name,
                    error=str(exc),
                    nome=nome,
                    email=email,
                    cargo=cargo,
                    crm_coren=crm_coren,
                    admin=admin,
                )

            if redirect_para_login:
                return redirect(url_for("login", mensagem="Usuário cadastrado com sucesso"))
            return render_template(template_name, success="Usuário cadastrado com sucesso")

        return render_template(template_name)

    @staticmethod
    def cadastro():
        return AuthController._processar_cadastro("cadastro.html", redirect_para_login=False)

    @staticmethod
    def primeiro_cadastro():
        global CHAVE_CADASTRO_ATUAL

        chave_param = request.args.get('chave')

        if request.method == "GET" and (CHAVE_CADASTRO_ATUAL is None or chave_param != CHAVE_CADASTRO_ATUAL):
            flash("Esta chave de cadastro expirou ou já foi utilizada.", "danger")
            pagina_anterior = request.referrer

            if not pagina_anterior:
                pagina_anterior = url_for('dashboard')

            return redirect(pagina_anterior)

        if request.method == "POST":
            if CHAVE_CADASTRO_ATUAL is None or chave_param != CHAVE_CADASTRO_ATUAL:
                flash("Esta chave de cadastro expirou ou já foi utilizada.", "danger")
                pagina_anterior = request.referrer

                if not pagina_anterior:
                    pagina_anterior = url_for('dashboard')

                return redirect(pagina_anterior)

            resultado = AuthController._processar_cadastro("primeiro_cadastro.html", redirect_para_login=True)
            if isinstance(resultado, str):
                return resultado

            CHAVE_CADASTRO_ATUAL = None
            return resultado

        return render_template("primeiro_cadastro.html")

    @staticmethod
    def login():
        if "usuario" in session:
            usuario = session["usuario"]
            admin_value = Usuario.normalizar_perfil(usuario.get("admin", "nao"))
            if admin_value == "admin":
                return redirect(url_for("usuarios"))
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            crm_coren = request.form.get("crm_coren", "").strip()
            senha = request.form.get("senha", "").strip()
            mensagem = request.args.get("mensagem")

            if not crm_coren or not senha:
                return render_template("login.html", success=mensagem, CHAVE_CADASTRO_ATUAL=CHAVE_CADASTRO_ATUAL)

            usuario = Usuario.autenticar(crm_coren, senha)
            if usuario:
                try:
                    dados_sessao = {
                        "id": usuario["id"],
                        "nome": usuario["nome"],
                        "email": usuario["email"],
                        "cargo": usuario["cargo"],
                        "crm_coren": de(usuario.get("crm_coren", "")),
                        "admin": Usuario.normalizar_perfil(usuario.get("admin", "nao")),
                        "assinatura": usuario["assinatura"]
                    }
                    admin_value = Usuario.normalizar_perfil(usuario.get("admin", "nao"))
                except (KeyError, TypeError):
                    dados_sessao = {
                        "id": usuario[0],
                        "crm_coren": de(usuario[1]),
                        "nome": usuario[2],
                        "email": usuario[3],
                        "cargo": usuario[4],
                        "admin": Usuario.normalizar_perfil(usuario[6]),
                        "assinatura": usuario[7]
                    }
                    admin_value = Usuario.normalizar_perfil(usuario[6])

                session["usuario"] = dados_sessao

                if admin_value == "admin":
                    return redirect(url_for("usuarios"))
                return redirect(url_for("dashboard"))
            else:
                return render_template("login.html", error="CRM/COREN ou Senha incorretos", success=mensagem, CHAVE_CADASTRO_ATUAL=CHAVE_CADASTRO_ATUAL)

        return render_template("login.html", success=request.args.get("mensagem"), CHAVE_CADASTRO_ATUAL=CHAVE_CADASTRO_ATUAL)
    @staticmethod
    def usuarios():
        if "usuario" not in session:
            return redirect(url_for("login"))
        
        usuarios_db = Usuario.listar_todos()
        usuarios_lista = []
        for u in usuarios_db:
            if isinstance(u, dict):
                row = u
            elif hasattr(u, "keys"):
                row = dict(u)
            else:
                row = None

            if row is not None:
                usuarios_lista.append({
                    "id": row.get("id"),
                    "nome": row.get("nome", ""),
                    "email": row.get("email", ""),
                    "cargo": row.get("cargo", ""),
                    "crm_coren": de(row.get("crm_coren", "")),
                    "admin": Usuario.normalizar_perfil(row.get("admin", "nao")),
                    "assinatura": de(row.get("assinatura", ""))
                })
            else:
                usuarios_lista.append({
                    "id": u[0],
                    "nome": u[1],
                    "email": u[2],
                    "cargo": u[3],
                    "crm_coren": de(u[4]) if len(u) > 4 else "",
                    "admin": Usuario.normalizar_perfil(u[6] if len(u) > 6 else "nao"),
                    "assinatura": de(u[7]) if len(u) > 7 else ""
                })
        return render_template("usuarios.html", usuarios=usuarios_lista)

    @staticmethod
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @staticmethod
    def editar_usuario_post(usuario_id):
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()
        admin = Usuario.normalizar_perfil(request.form.get("admin", "nao"))
        crm_coren = request.form.get("crm_coren", "").strip() or None

        file = request.files.get("assinatura")
        assinatura_filename = None

        if file and file.filename != "":
            filename = f"{int(time.time())}_{secure_filename(file.filename)}"
            upload_path = os.path.join("static", "uploads")
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            assinatura_filename = filename

        # Passamos a "senha" para o banco de dados em vez do "cargo"
        Usuario.atualizar(usuario_id, nome, email, senha, admin, assinatura_filename, crm_coren)
        return redirect(url_for("usuarios"))
    
    @staticmethod
    def perfil():
        # Se o usuário enviou o formulário (Clicou em Salvar)
        if request.method == "POST":
            usuario_id = session["usuario"]["id"]  # Usando o ID como identificador único
            nome = request.form.get("nome", "").strip()
            email = request.form.get("email", "").strip()
            senha = request.form.get("senha", "").strip()
            
            # Repare: Nós NÃO capturamos 'cargo' nem 'crm_coren' do request.form.
            # Mesmo que um hacker tente forçar o envio desses dados, o Python vai ignorar.

            file = request.files.get("assinatura")
            assinatura_filename = None

            # Lógica de salvar a imagem
            if file and file.filename != "":
                filename = f"{int(time.time())}_{secure_filename(file.filename)}"
                upload_path = os.path.join("static", "uploads")
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                assinatura_filename = filename

            # Chama a função que criamos no usuario.py
            from usuario import Usuario
            Usuario.atualizar_perfil(session["usuario"]["id"], nome, email, senha if senha else None, assinatura_filename)

            # Atualiza os dados na "memória" (sessão) para a tela não mostrar dados antigos
            session["usuario"]["nome"] = nome
            session["usuario"]["email"] = email
            if assinatura_filename:
                session["usuario"]["assinatura"] = assinatura_filename
            session.modified = True

            # Redireciona de volta para a tela de perfil para ver as mudanças
            return redirect(url_for("dashboard"))

        # Se a requisição for GET (Apenas acessando a página)
        return render_template("perfil.html", usuario=session["usuario"])