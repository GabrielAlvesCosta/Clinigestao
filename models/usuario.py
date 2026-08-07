import sqlite3
from models.models import get_db, en, de
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario:
    def __init__(self, nome, email, cargo, crm_coren, senha, admin="nao", assinatura=""):
        self.nome = nome
        self.email = email
        self.cargo = cargo
        self.crm_coren = crm_coren
        self.senha = senha
        self.admin = admin
        self.assinatura = assinatura

    @staticmethod
    def normalizar_perfil(valor):
        if valor is None:
            return "comum"

        valor_texto = str(valor).strip().lower()
        if valor_texto in ("sim", "admin", "adm", "administrador"):
            return "admin"
        if valor_texto in ("atendente", "atendente"):
            return "atendente"
        if valor_texto in ("nao", "não", "comum", "usuario", "usuario comum", "user", "comum(usuario)"):
            return "comum"
        return "comum"

    def salvar(self):
        hashed_senha = generate_password_hash(self.senha)
        perfil = self.normalizar_perfil(self.admin)
        with get_db() as conexao:
            crm_value = str(self.crm_coren or "").strip()
            if crm_value:
                rows = conexao.execute(
                    "SELECT id, crm_coren FROM usuarios WHERE crm_coren IS NOT NULL"
                ).fetchall()
                for row in rows:
                    stored_value = row[1]
                    if stored_value and de(stored_value) == crm_value:
                        raise ValueError("CRM/COREN já cadastrado")
            try:
                conexao.execute(
                    """
                    INSERT INTO usuarios (nome, email, cargo, crm_coren, senha, admin, assinatura)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (self.nome, self.email, self.cargo, en(self.crm_coren), hashed_senha, perfil, en(self.assinatura))
                )
                conexao.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("CRM/COREN já cadastrado") from exc
    
    @staticmethod
    def atualizar_perfil(usuario_id, nome, email, senha=None, assinatura_filename=None):
        # CORREÇÃO: Importamos a conexão correta do nosso models unificado
        # Começamos atualizando apenas o básico
        query = "UPDATE usuarios SET nome = ?, email = ?"
        params = [nome, email]

        # Se o usuário digitou uma senha nova, nós a criptografamos e adicionamos na query
        if senha:
            from werkzeug.security import generate_password_hash
            query += ", senha = ?"
            params.append(generate_password_hash(senha))

        # Se o usuário enviou um novo arquivo de assinatura, atualizamos a foto
        if assinatura_filename:
            query += ", assinatura = ?"
            params.append(en(assinatura_filename))
            
        # Finaliza a query apontando para o usuário correto
        query += " WHERE id = ?"
        params.append(usuario_id)
        
        # CORREÇÃO: Usamos o get_db() em vez de db.conectar()
        with get_db() as conexao:
            conexao.execute(query, tuple(params))
            conexao.commit()
    @staticmethod
    def atualizar(usuario_id, nome, email, senha, admin, assinatura_filename=None, crm_coren=None):
        perfil = Usuario.normalizar_perfil(admin)
        query = "UPDATE usuarios SET nome = ?, email = ?, admin = ?"
        params = [nome, email, perfil]

        if crm_coren is not None:
            with get_db() as conexao:
                crm_value = str(crm_coren or "").strip()
                if crm_value:
                    for row in conexao.execute("SELECT id, crm_coren FROM usuarios WHERE id != ?", (usuario_id,)).fetchall():
                        stored_value = row[1]
                        if stored_value and de(stored_value) == crm_value:
                            raise ValueError("CRM/COREN já cadastrado")
                query += ", crm_coren = ?"
                params.append(en(crm_coren))
        
        if senha:
            hashed_senha = generate_password_hash(senha)
            query += ", senha = ?"
            params.append(hashed_senha)
            
        if assinatura_filename:
            query += ", assinatura = ?"
            params.append(en(assinatura_filename))
            
        query += " WHERE id = ?"
        params.append(usuario_id)
        
        with get_db() as conexao:
            conexao.execute(query, tuple(params))
            conexao.commit()

    @staticmethod
    def buscar_por_email(email):
        with get_db() as conexao:
            cursor = conexao.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
            return cursor.fetchone()

    @staticmethod
    def listar_todos():
        with get_db() as conexao:
            cursor = conexao.execute("SELECT * FROM usuarios ORDER BY id ASC")
            return cursor.fetchall()

    @staticmethod
    def email_existe(email):
        return Usuario.buscar_por_email(email) is not None

    @staticmethod
    def autenticar(login_id, senha):
        with get_db() as conexao:
            cursor = conexao.execute("SELECT * FROM usuarios")
            for usuario_row in cursor.fetchall():
                usuario = dict(usuario_row)
                if usuario.get('email') == login_id or de(usuario.get('crm_coren')) == login_id:
                    if check_password_hash(usuario['senha'], senha):
                        usuario['crm_coren'] = de(usuario.get('crm_coren'))
                        usuario['assinatura'] = de(usuario.get('assinatura'))
                        usuario['admin'] = Usuario.normalizar_perfil(usuario.get('admin'))
                        return usuario
            return None