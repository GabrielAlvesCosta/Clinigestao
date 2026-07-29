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
        for table, column in [
            ("usuarios", "crm_coren"),
            ("usuarios", "assinatura"),
            ("consultas", "crm_coren"),
            ("prontuarios", "crm_coren"),
            ("auditoria", "crm_coren"),
        ]:
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
        
        # TABELA DEFINITIVA DE USUÁRIOS
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
        
        # TABELAS CLÍNICAS (Ligadas ao ID do Usuário)
        c.execute('''
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                dataNasc TEXT NOT NULL,
                genero TEXT NOT NULL,
                documento TEXT NOT NULL,
                cartao TEXT NOT NULL,
                contato TEXT NOT NULL
            )
        ''')
        
        # CORREÇÃO: REFERENCES usuarios(crm_coren)
        c.execute('''
            CREATE TABLE IF NOT EXISTS consultas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pacienteId INTEGER, nomePaciente TEXT, data TEXT, horario TEXT,
                crm_coren TEXT, status TEXT,
                FOREIGN KEY (pacienteId) REFERENCES pacientes(id),
                FOREIGN KEY (crm_coren) REFERENCES usuarios(crm_coren) 
            )
        ''')
        
        # CORREÇÃO: REFERENCES usuarios(crm_coren)
        c.execute('''
            CREATE TABLE IF NOT EXISTS prontuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pacienteId INTEGER, nomePaciente TEXT, dataNascimento TEXT, genero TEXT,
                documento TEXT, convenioCartao TEXT, contatoPaciente TEXT, acompanhante TEXT,
                especialidade TEXT, tipoAtendimento TEXT, prioridade TEXT,
                registroProfissional TEXT, carimboAssinatura TEXT, qp TEXT, hda TEXT, hmp TEXT, alergias TEXT,
                sinalPA TEXT, sinalFC TEXT, sinalFR TEXT, sinalTEMP TEXT, sinalSATO2 TEXT,
                peso TEXT, altura TEXT,
                estadoGeral TEXT, cardioResp TEXT, neuroOutros TEXT, hipotese TEXT, conduta TEXT,
                crm_coren TEXT,
                FOREIGN KEY (pacienteId) REFERENCES pacientes(id),
                FOREIGN KEY (crm_coren) REFERENCES usuarios(crm_coren)
            )
        ''')

        # CORREÇÃO: REFERENCES usuarios(crm_coren)
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