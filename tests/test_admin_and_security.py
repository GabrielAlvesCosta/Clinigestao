import os
import pytest
import app as meu_app
import models as meus_models
from usuario import Usuario


@pytest.fixture
def client():
    meu_app.app.config['TESTING'] = True
    db_path = f"clinica_test_{os.getpid()}.db"
    meus_models.DB_FILE = db_path

    for arquivo in [db_path, 'clinica.db', 'clinica_test.db', 'clinica_test_debug.db', 'lgpd_secret.key']:
        if os.path.exists(arquivo):
            try:
                os.remove(arquivo)
            except Exception:
                pass

    with meu_app.app.app_context():
        meu_app.init_db()

    with meu_app.app.test_client() as client_test:
        yield client_test


def test_adm_route_redirects_to_admin_panel_for_admin_user(client):
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

    response = client.get('/adm')
    assert response.status_code == 302
    assert response.headers['Location'] == '/usuarios'


def test_users_page_renders_with_sqlite_rows(client):
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

    Usuario('Dr. A', 'dr_a@test.com', 'Médico', 'CRM-123', 'senha123', 'nao', '').salvar()

    response = client.get('/usuarios')
    assert response.status_code == 200
    assert b'Dr. A' in response.data


def test_crm_coren_is_encrypted_and_unique(client):
    with meu_app.app.app_context():
        Usuario('Dr. A', 'dr_a@test.com', 'Médico', 'CRM-123', 'senha123', 'nao', '').salvar()

        with pytest.raises(ValueError):
            Usuario('Dr. B', 'dr_b@test.com', 'Médico', 'CRM-123', 'senha123', 'nao', '').salvar()

        row = meus_models.get_db().execute(
            'SELECT crm_coren FROM usuarios WHERE email = ?', ('dr_a@test.com',)
        ).fetchone()

        assert row['crm_coren'] != 'CRM-123'
        assert row['crm_coren'].startswith('gAAAAA')
