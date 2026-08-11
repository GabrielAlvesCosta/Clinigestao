import gc
import json
import sqlite3
from io import BytesIO
import pytest
from unittest.mock import patch, MagicMock
from werkzeug.security import check_password_hash

import app as meu_app
import models.models as meus_models
from models.usuario import Usuario


@pytest.fixture
def client(tmp_path):
    # 1. Configuração de Teste[cite: 21]
    meu_app.app.config['TESTING'] = True

    # 2. Cria o banco de dados dentro do diretório temporário do Pytest[cite: 21]
    db_file = tmp_path / "clinica_test.db"
    meus_models.DB_FILE = str(db_file)

    # 3. Inicializa o banco de dados temporário[cite: 21]
    with meu_app.app.app_context():
        meu_app.init_db()

    # 4. Executa os testes[cite: 21]
    with meu_app.app.test_client() as client_test:
        yield client_test

    # 5. Força a liberação de conexões do SQLite mantidas na memória[cite: 21]
    gc.collect()


# ==========================================
# TESTES ORIGINAIS (1 a 3)
# ==========================================

def test_01_adm_route_redirects_to_admin_panel_for_admin_user(client):
    with client.session_transaction() as sess:
        sess['usuario'] = {
            'id': 1,
            'nome': 'Admin',
            'email': 'admin@test.com',
            'cargo': 'Gerente',
            'crm_coren': '12345',
            'admin': 'sim',
            'assinatura': ''
        } #[cite: 21]

    response = client.get('/adm') #[cite: 21]
    assert response.status_code == 302 #[cite: 21]
    assert response.headers['Location'] == '/usuarios' #[cite: 21]


def test_02_users_page_renders_with_sqlite_rows(client):
    with client.session_transaction() as sess:
        sess['usuario'] = {
            'id': 1,
            'nome': 'Admin',
            'email': 'admin@test.com',
            'cargo': 'Gerente',
            'crm_coren': '12345',
            'admin': 'sim',
            'assinatura': ''
        } #[cite: 21]

    Usuario('Dr. A', 'dr_a@test.com', 'Médico', 'CRM-123', 'senha123', 'nao', '').salvar() #[cite: 21]

    response = client.get('/usuarios') #[cite: 21]
    assert response.status_code == 200 #[cite: 21]
    assert b'Dr. A' in response.data #[cite: 21]


def test_03_crm_coren_is_encrypted_and_unique(client):
    with meu_app.app.app_context():
        Usuario('Dr. A', 'dr_a@test.com', 'Médico', 'CRM-123', 'senha123', 'nao', '').salvar() #[cite: 21]

        with pytest.raises(ValueError):
            Usuario('Dr. B', 'dr_b@test.com', 'Médico', 'CRM-123', 'senha123', 'nao', '').salvar() #[cite: 21]

        conn = meus_models.get_db() #[cite: 21]
        try:
            row = conn.execute(
                'SELECT crm_coren FROM usuarios WHERE email = ?', ('dr_a@test.com',)
            ).fetchone() #[cite: 21]
        finally:
            conn.close() #[cite: 21]

        assert row['crm_coren'] != 'CRM-123' #[cite: 21]
        assert row['crm_coren'].startswith('gAAAAA') #[cite: 21]


# ==========================================
# TESTES UNITÁRIOS PUROS (4 a 10)
# ==========================================

def test_04_unit_encryption_oculta_dados():
    resultado = meus_models.en("informacao_sensivel")
    assert resultado != "informacao_sensivel"
    assert resultado.startswith("gAAAAA")

def test_05_unit_decryption_restaura_dados_corretamente():
    texto_original = "dados_do_paciente"
    texto_criptografado = meus_models.en(texto_original)
    assert meus_models.de(texto_criptografado) == texto_original

def test_06_unit_looks_encrypted_valida_formato():
    assert meus_models._looks_encrypted("gAAAAA_meu_token_falso") is True
    assert meus_models._looks_encrypted("texto_normal") is False
    assert meus_models._looks_encrypted(None) is False

def test_07_unit_funcoes_criptografia_ignoram_vazios():
    assert meus_models.en("") == ""
    assert meus_models.de(None) is None

def test_08_unit_usuario_instanciacao():
    u = Usuario("Ana", "ana@teste.com", "Enfermeira", "COREN-999", "senha123")
    assert u.nome == "Ana"
    assert u.admin == "nao"
    assert u.assinatura == ""

@patch('models.usuario.Usuario.buscar_por_email')
def test_09_unit_email_existe_com_mock(mock_buscar):
    mock_buscar.return_value = {"id": 1, "nome": "Mocked"}
    assert Usuario.email_existe("qualquer@email.com") is True

@patch('models.usuario.get_db')
def test_10_unit_senha_invalida_nao_autentica_mockado(mock_get_db):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [{
        "id": 1, 
        "email": "medico@teste.com", 
        "crm_coren": meus_models.en("CRM-123"),
        "senha": "pbkdf2:sha256:600000$teste$falsohash", 
        "assinatura": ""
    }]
    mock_get_db.return_value.__enter__.return_value.execute.return_value = mock_cursor

    usuario_autenticado = Usuario.autenticar("medico@teste.com", "senha_errada")
    assert usuario_autenticado is None


# ==========================================
# TESTES DE INTEGRAÇÃO (11 a 15)
# ==========================================

def test_11_integ_cadastro_paciente_salva_no_banco_corretamente(client):
    res = client.post('/api/pacientes', json={
        "nome": "João", "dataNasc": "1990-01-01", "genero": "M", 
        "documento": "123", "cartao": "456", "contato": "9999"
    })
    assert res.status_code == 201
    
    conn = sqlite3.connect(meus_models.DB_FILE)
    linhas = conn.execute("SELECT id FROM pacientes").fetchall()
    conn.close()
    assert len(linhas) == 1

def test_12_integ_atualizar_perfil_usuario_reflete_no_banco(client):
    with meu_app.app.app_context():
        Usuario("Dra. B", "b@teste.com", "Médica", "CRM-001", "123").salvar()
        u = Usuario.buscar_por_email("b@teste.com")
        
        Usuario.atualizar_perfil(u['id'], "Dra. B Atualizada", "b@teste.com")
        u_atualizado = Usuario.buscar_por_email("b@teste.com")
        
        assert u_atualizado['nome'] == "Dra. B Atualizada"

def test_13_integ_consulta_requisita_paciente_valido(client):
    res = client.post('/api/consultas', json={
        "pacienteId": 999,  
        "crm_coren": "CRM-123"
    })
    assert res.status_code == 400
    assert b"error" in res.data

def test_14_integ_listar_usuarios_mapeia_dados_corretamente(client):
    with meu_app.app.app_context():
        Usuario("User 1", "u1@teste.com", "Cargo", "CRM-1", "123").salvar()
        Usuario("User 2", "u2@teste.com", "Cargo", "CRM-2", "123").salvar()
        
        usuarios = Usuario.listar_todos()
        assert len(usuarios) == 2

def test_15_integ_auditoria_disparada_na_criacao_de_prontuario(client):
    with meu_app.app.app_context():
        Usuario("Profissional", "prof@teste.com", "Med", "CRM-99", "123").salvar()
    client.post('/api/pacientes', json={"nome": "Paciente Z"})
    
    with client.session_transaction() as sess:
        sess['usuario'] = {"crm_coren": "CRM-99", "nome": "Profissional"}
    
    client.post('/api/prontuarios', json={"pacienteId": 1, "qp": "Dor de cabeça"})
    
    auditoria = json.loads(client.get('/api/prontuarios/auditoria').data)
    assert len(auditoria) == 1
    assert auditoria[0]['acao'] == "Criação"


# ==========================================
# TESTES FUNCIONAIS (16 a 20)
# ==========================================

def test_16_func_login_valido_redireciona_dashboard(client):
    with meu_app.app.app_context():
        Usuario("Médico C", "c@teste.com", "Med", "CRM-3", "senha_forte").salvar()
        
    res = client.post('/login', data={"email": "c@teste.com", "senha": "senha_forte"})
    assert res.status_code == 302
    assert "/dashboard" in res.headers['Location']

def test_17_func_dashboard_protegido_sem_login(client):
    res = client.get('/dashboard')
    assert res.status_code == 302
    assert "/login" in res.headers['Location']

def test_18_func_logout_limpa_sessao(client):
    with client.session_transaction() as sess:
        sess['usuario'] = {"id": 1}
        
    res = client.get('/logout')
    assert res.status_code == 302
    
    with client.session_transaction() as sess:
        assert "usuario" not in sess

def test_19_func_acesso_tela_cadastro_carrega_corretamente(client):
    res = client.get('/cadastro')
    assert res.status_code == 200
    assert b"Cadastro" in res.data

def test_20_func_acesso_negado_adm_para_usuario_comum(client):
    with client.session_transaction() as sess:
        sess['usuario'] = {"admin": "nao"}
        
    res = client.get('/adm')
    assert res.status_code == 302
    assert "/dashboard" in res.headers['Location']


# ==========================================
# TESTES DE SEGURANÇA (21 a 25)
# ==========================================

def test_21_sec_senhas_nunca_salvas_em_texto_plano(client):
    with meu_app.app.app_context():
        Usuario("Hacker", "h@teste.com", "Cargo", "CRM-H", "senha_secreta").salvar()
        
        conn = sqlite3.connect(meus_models.DB_FILE)
        senha_no_banco = conn.execute("SELECT senha FROM usuarios WHERE email='h@teste.com'").fetchone()[0]
        conn.close()
        
        assert senha_no_banco != "senha_secreta"
        assert check_password_hash(senha_no_banco, "senha_secreta") is True

def test_22_sec_rota_edicao_usuario_bloqueada_sem_sessao(client):
    res = client.post('/usuarios/editar/1', data={"nome": "Mudou"})
    assert res.status_code == 302
    assert "/login" in res.headers['Location']


def test_23_users_page_has_link_to_cadastro_page(client):
    with client.session_transaction() as sess:
        sess['usuario'] = {
            'id': 1,
            'nome': 'Admin',
            'email': 'admin@test.com',
            'cargo': 'Gerente',
            'crm_coren': '12345',
            'admin': 'sim',
            'assinatura': ''
        }

    response = client.get('/usuarios')
    assert response.status_code == 200
    assert b'Cadastrar Usu\xc3\xa1rio' in response.data
    assert b'/cadastro?chave=MED2026' in response.data


def test_24_cadastro_success_stays_on_page_and_shows_message(client):
    response = client.post('/cadastro?chave=MED2026', data={
        'nome': 'Novo Usuário',
        'email': 'novo@test.com',
        'cargo': 'Enfermeiro',
        'crm_coren': 'CRM-999',
        'senha': 'senha123',
        'confirmar_senha': 'senha123',
        'admin': 'comum',
        'assinatura': (BytesIO(b'fake-image-data'), 'assinatura.png'),
    }, content_type='multipart/form-data')

    assert response.status_code == 200
    assert b'Usu\xc3\xa1rio cadastrado com sucesso' in response.data
    assert b'Cadastro de Usu\xc3\xa1rios' in response.data


def test_25_cadastro_page_has_navigation_buttons(client):
    response = client.get('/cadastro?chave=MED2026')
    assert response.status_code == 200
    assert b'/usuarios' in response.data
    assert b'/dashboard' in response.data


def test_23_cadastro_aceita_perfil_comum(client):
    arquivo = (BytesIO(b"fake-image"), "assinatura.png")

    response = client.post('/cadastro', data={
        "nome": "Usuário Comum",
        "email": "comum@test.com",
        "cargo": "Recepcionista",
        "crm_coren": "",
        "senha": "senha123",
        "confirmar_senha": "senha123",
        "admin": "comum",
        "assinatura": arquivo,
    }, content_type='multipart/form-data')

    assert response.status_code == 302
    assert response.headers['Location'] == '/login'

    with meu_app.app.app_context():
        usuario = Usuario.buscar_por_email('comum@test.com')
        assert usuario is not None
        assert usuario['admin'] == 'comum'

def test_23_sec_tentativa_sql_injection_login_falha(client):
    payload_sqli = "admin@teste.com' OR '1'='1"
    res = client.post('/login', data={"email": payload_sqli, "senha": "123"})
    assert b"incorretos" in res.data 
    assert res.status_code == 200

def test_24_sec_protecao_xss_nos_campos_do_paciente(client):
    xss_payload = "<script>alert('XSS')</script>"
    client.post('/api/pacientes', json={"nome": xss_payload})
    
    res = client.get('/api/pacientes')
    pacientes = json.loads(res.data)
    
    assert pacientes[0]['nome'] == xss_payload