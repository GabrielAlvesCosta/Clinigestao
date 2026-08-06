import sqlite3
import os
from cryptography.fernet import Fernet


KEY_FILE = 'lgpd_secret.key'
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'wb') as f:
        f.write(Fernet.generate_key())

with open(KEY_FILE, 'rb') as f:
    FERNET_KEY = f.read()

cipher = Fernet(FERNET_KEY)


def _looks_encrypted(value):
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text.startswith("gAAAAA")


def en(value):
    if value is None or str(value).strip() == '':
        return value
    if _looks_encrypted(value):
        return str(value)
    return cipher.encrypt(str(value).encode('utf-8')).decode('utf-8')


def de(value):
    if value is None or str(value).strip() == '':
        return value
    if not _looks_encrypted(value):
        return str(value)
    try:
        return cipher.decrypt(str(value).encode('utf-8')).decode('utf-8')
    except Exception:
        return str(value)


DB_FILE = 'clinica.db'


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON") 
    conn.row_factory = sqlite3.Row
    return conn


def migrate_sensitive_fields():
    with get_db() as conn:
        cursor = conn.cursor()
        campos_sensiveis = [
            ("usuarios", "crm_coren"),
            ("usuarios", "assinatura"),
            ("pacientes", "documento"),
            ("consultas", "crm_coren"),
            ("consultas", "documento"),
            ("prontuarios", "crm_coren"),
            ("prontuarios", "documento"),
            ("auditoria", "crm_coren"),
        ]
        
        for table, column in campos_sensiveis:
            try:
                rows = cursor.execute(f"SELECT id, {column} FROM {table}").fetchall()
            except sqlite3.Error:
                continue

            for row in rows:
                value = row[1]
                if value is None or str(value).strip() == "" or _looks_encrypted(value):
                    continue
                cursor.execute(f"UPDATE {table} SET {column} = ? WHERE id = ?", (en(value), row[0]))
        conn.commit()


def init_db():
    with get_db() as conn:
        c = conn.cursor()
        
        # 1. TABELA DE USUÁRIOS
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crm_coren TEXT UNIQUE,
                nome TEXT,
                email TEXT UNIQUE,
                cargo TEXT,
                senha TEXT,
                admin TEXT DEFAULT 'nao',
                assinatura TEXT DEFAULT ''
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                dataNasc TEXT NOT NULL,
                genero TEXT NOT NULL,
                documento TEXT NOT NULL UNIQUE,
                cartao TEXT NOT NULL,
                contato TEXT NOT NULL
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS consultas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pacienteId INTEGER,
                documento TEXT,
                nomePaciente TEXT,
                data TEXT,
                horario TEXT,
                crm_coren TEXT,
                status TEXT,
                FOREIGN KEY (pacienteId) REFERENCES pacientes(id),
                FOREIGN KEY (documento) REFERENCES pacientes(documento),
                FOREIGN KEY (crm_coren) REFERENCES usuarios(crm_coren) 
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS prontuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pacienteId INTEGER,
                documento TEXT,
                nomePaciente TEXT,
                dataNascimento TEXT,
                genero TEXT,
                convenioCartao TEXT,
                contatoPaciente TEXT,
                acompanhante TEXT,
                especialidade TEXT,
                tipoAtendimento TEXT,
                prioridade TEXT,
                registroProfissional TEXT,
                carimboAssinatura TEXT,
                qp TEXT,
                hda TEXT,
                hmp TEXT,
                alergias TEXT,
                sinalPA TEXT,
                sinalFC TEXT,
                sinalFR TEXT,
                sinalTEMP TEXT,
                sinalSATO2 TEXT,
                peso TEXT,
                altura TEXT,
                estadoGeral TEXT,
                cardioResp TEXT,
                neuroOutros TEXT,
                hipotese TEXT,
                conduta TEXT,
                crm_coren TEXT,
                FOREIGN KEY (pacienteId) REFERENCES pacientes(id),
                FOREIGN KEY (documento) REFERENCES pacientes(documento),
                FOREIGN KEY (crm_coren) REFERENCES usuarios(crm_coren)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                nome_profissional TEXT,
                crm_coren TEXT,
                acao TEXT,
                prontuario_id INTEGER,
                nome_paciente TEXT,
                FOREIGN KEY (crm_coren) REFERENCES usuarios(crm_coren),
                FOREIGN KEY (prontuario_id) REFERENCES prontuarios(id)
            )
        ''')
        conn.commit()
        migrate_sensitive_fields()



def buscar_por_documento(documento):
    if not documento:
        return None
        
    doc_alvo = str(documento).strip()
    conn = get_db()
    try:
        pacientes = conn.execute("SELECT * FROM pacientes").fetchall()
        for p in pacientes:
            p_dict = dict(p)
            doc_descriptografado = de(p_dict['documento']) 
            if doc_descriptografado == doc_alvo:
                p_dict['nome'] = de(p_dict.get('nome'))
                p_dict['dataNasc'] = de(p_dict.get('dataNasc'))
                p_dict['genero'] = de(p_dict.get('genero'))
                p_dict['documento'] = doc_descriptografado
                p_dict['cartao'] = de(p_dict.get('cartao'))
                p_dict['contato'] = de(p_dict.get('contato'))
                return p_dict
    finally:
        conn.close()
        
    return None


def listar_consultas_por_documento(documento):
    paciente = buscar_por_documento(documento)
    if not paciente:
        return []

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM consultas WHERE pacienteId = ?", (paciente['id'],)
        ).fetchall()
        
        consultas = []
        for r in rows:
            c_dict = dict(r)
            c_dict['nomePaciente'] = de(c_dict.get('nomePaciente'))
            c_dict['documento'] = paciente['documento']
            c_dict['crm_coren'] = de(c_dict.get('crm_coren'))
            consultas.append(c_dict)
        return consultas
    finally:
        conn.close()


def listar_prontuarios_por_documento(documento):
    paciente = buscar_por_documento(documento)
    if not paciente:
        return []

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM prontuarios WHERE pacienteId = ?", (paciente['id'],)
        ).fetchall()
        
        prontuarios = []
        for r in rows:
            p_dict = dict(r)
            p_dict['nomePaciente'] = de(p_dict.get('nomePaciente'))
            p_dict['documento'] = paciente['documento']
            p_dict['crm_coren'] = de(p_dict.get('crm_coren'))
            
            for campo in ['qp', 'hda', 'hmp', 'alergias', 'hipotese', 'conduta', 'registroProfissional', 'carimboAssinatura']:
                if campo in p_dict:
                    p_dict[campo] = de(p_dict[campo])
            prontuarios.append(p_dict)
            
        return prontuarios
    finally:
        conn.close()