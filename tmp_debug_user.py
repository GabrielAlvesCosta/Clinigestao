import os
import models as meus_models
import app as meu_app
from usuario import Usuario

for f in ['clinica_test_single.db', 'clinica_test_debug.db', 'clinica_test.db', 'clinica.db', 'lgpd_secret.key']:
    if os.path.exists(f):
        os.remove(f)

db_path = 'clinica_test_single.db'
meus_models.DB_FILE = db_path
print('DB_FILE set to', meus_models.DB_FILE)
meu_app.app.config['TESTING'] = True
with meu_app.app.app_context():
    meu_app.init_db()
    print('tables created')
    print('before save rows', meus_models.get_db().execute('SELECT id, crm_coren FROM usuarios').fetchall())
    try:
        Usuario('Dr. A','dr_a@test.com','Médico','CRM-123','senha123','nao','').salvar()
        print('saved ok')
    except Exception as e:
        print('error', type(e).__name__, e)
        print('rows after fail', meus_models.get_db().execute('SELECT id, crm_coren FROM usuarios').fetchall())
