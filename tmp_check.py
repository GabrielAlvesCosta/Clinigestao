import os
import app as meu_app
import models as meus_models
from usuario import Usuario

os.remove('clinica_test.db') if os.path.exists('clinica_test.db') else None
meus_models.DB_FILE = 'clinica_test.db'
with meu_app.app.app_context():
    meu_app.init_db()
    try:
        Usuario('Dr. A', 'dr_a@test.com', 'Médico', 'CRM-123', 'senha123', 'nao', '').salvar()
        print('first ok')
        Usuario('Dr. B', 'dr_b@test.com', 'Médico', 'CRM-123', 'senha123', 'nao', '').salvar()
        print('second ok')
    except Exception as e:
        print(type(e).__name__, e)
