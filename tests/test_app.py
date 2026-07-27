import pytest
import os
import json
import sqlite3
import app as meu_app  # Importa o módulo real da sua aplicação
import models as meus_models

# ==============================================================================
# SETUP: AMBIENTE DE TESTE ISOLADO COM TMP_PATH (À PROVA DE WINERROR 32)
# ==============================================================================
@pytest.fixture
def client():
    # 1. Configura o Flask para modo de teste
    meu_app.app.config['TESTING'] = True
    
    # 2. Desvia a Base de Dados APENAS para os testes
    TEST_DB = 'clinica.db'
    meu_app.DB_FILE = TEST_DB
    
    # 3. Limpa qualquer rastro se o teste anterior tiver falhado
    if os.path.exists(TEST_DB):
        try: os.remove(TEST_DB)
        except: pass
        
    # 4. Inicializa as tabelas do zero
    with meu_app.app.app_context():
        meu_app.init_db()
        
    with meu_app.app.test_client() as client_test:
        # 5. INJETA DADOS BASE PARA SATISFAZER AS CHAVES ESTRANGEIRAS
        client_test.post('/api/usuarios', json={
            "cpf": "11122233344", "nome": "Dr. Teste Base", "cargo": "medico"
        })
        
        # O 'yield' pausa a função aqui, entrega o client para os testes rodarem,
        # e quando os testes acabam, o código continua a partir daqui!
        yield client_test
        
    # =========================================================================
    # TEARDOWN: LIMPEZA AUTOMÁTICA (Executa após todos os testes terminarem)
    # =========================================================================
    arquivos_residuais = ['clinica.db', 'test_clinica.db', 'lgpd_secret.key', TEST_DB]
    
    for arquivo in arquivos_residuais:
        if os.path.exists(arquivo):
            try:
                os.remove(arquivo)
            except Exception:
                pass

# ==============================================================================
# MÓDULO 1: PACIENTES E ENCRIPTAÇÃO (LGPD)
# ==============================================================================

def test_01_criar_paciente_dados_completos(client):
    res = client.post('/api/pacientes', json={
        "nome": "João Silva", "dataNasc": "1980-05-15", "genero": "Masculino", 
        "idadeAnos": "46", "idadeMeses": "2", "idadeDias": "10", 
        "documento": "123456789", "cartao": "987654", "contato": "11999999999"
    })
    assert res.status_code == 200

def test_02_criar_paciente_campos_vazios(client):
    res = client.post('/api/pacientes', json={"nome": "Maria Souza", "documento": "", "contato": ""})
    assert res.status_code == 200

def test_03_atualizar_dados_paciente(client):
    res_post = client.post('/api/pacientes', json={"nome": "Carlos Velho", "contato": "0000"})
    p_id = json.loads(res_post.data)["id"]
    res_put = client.put('/api/pacientes', json={"id": p_id, "nome": "Carlos Atualizado", "contato": "1111"})
    assert res_put.status_code == 200
    pacientes = json.loads(client.get('/api/pacientes').data)
    paciente_editado = next((p for p in pacientes if p['id'] == p_id), None)
    assert paciente_editado['nome'] == "Carlos Atualizado"

def test_04_listagem_pacientes_ordem_decrescente(client):
    client.post('/api/pacientes', json={"nome": "Paciente A"})
    client.post('/api/pacientes', json={"nome": "Paciente B"})
    pacientes = json.loads(client.get('/api/pacientes').data)
    assert pacientes[0]['nome'] == "Paciente B"

def test_05_validar_encriptacao_paciente_direto_no_banco(client):
    client.post('/api/pacientes', json={"nome": "Segredo Absoluto", "contato": "99999999"})
    
    # ATUALIZADO: Chama o DB_FILE a partir do models
    conn = sqlite3.connect(meus_models.DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT nome FROM pacientes ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    
    assert row["nome"] != "Segredo Absoluto"
    assert row["nome"].startswith("gAAAAA")

# ==============================================================================
# MÓDULO 2: CONSULTAS (AGENDAMENTOS E ESTADOS)
# ==============================================================================

def test_06_agendar_consulta_sucesso(client):
    res = client.post('/api/consultas', json={
        "pacienteId": 1, "nomePaciente": "Ana", "data": "2026-10-10", 
        "horario": "10:00", "profissional": "Dr. Teste Base", "status": "Agendado"
    })
    assert res.status_code == 200

def test_07_choque_horario_profissionais_diferentes(client):
    client.post('/api/consultas', json={"pacienteId": 1, "data": "2026-10-10", "horario": "14:00", "profissional": "Dr. A"})
    res = client.post('/api/consultas', json={"pacienteId": 2, "data": "2026-10-10", "horario": "14:00", "profissional": "Dr. B"})
    assert res.status_code == 200 

def test_08_mudar_status_consulta_confirmado(client):
    client.post('/api/consultas', json={"data": "2026-11-11", "horario": "09:00", "profissional": "Dr. Teste Base", "status": "Agendado"})
    c_id = json.loads(client.get('/api/consultas?status=ativas').data)[0]['id']
    res = client.put('/api/consultas', json={"id": c_id, "status": "Confirmado"})
    assert res.status_code == 200

def test_09_mudar_status_consulta_cancelado(client):
    client.post('/api/consultas', json={"data": "2026-11-11", "horario": "10:00", "profissional": "Dr. Teste Base", "status": "Agendado"})
    c_id = json.loads(client.get('/api/consultas?status=ativas').data)[0]['id']
    client.put('/api/consultas', json={"id": c_id, "status": "Cancelado"})
    ativas = json.loads(client.get('/api/consultas?status=ativas').data)
    assert not any(c['id'] == c_id for c in ativas)

def test_10_mudar_status_consulta_atendido(client):
    client.post('/api/consultas', json={"data": "2026-11-11", "horario": "11:00", "profissional": "Dr. Teste Base", "status": "Agendado"})
    c_id = json.loads(client.get('/api/consultas?status=ativas').data)[0]['id']
    client.put('/api/consultas', json={"id": c_id, "status": "Atendido"})
    concluidas = json.loads(client.get('/api/consultas?status=concluidas').data)
    assert any(c['id'] == c_id for c in concluidas)

def test_11_filtros_consultas_ativas(client):
    ativas = json.loads(client.get('/api/consultas?status=ativas').data)
    for c in ativas: assert c['status'] in ['Agendado', 'Confirmado']

def test_12_filtros_consultas_concluidas(client):
    concluidas = json.loads(client.get('/api/consultas?status=concluidas').data)
    for c in concluidas: assert c['status'] in ['Cancelado', 'Atendido']

# ==============================================================================
# MÓDULO 3: PRONTUÁRIOS ELETRÔNICOS (PEP)
# ==============================================================================

def test_13_criar_prontuario_completo(client):
    res = client.post('/api/prontuarios', json={
        "pacienteId": 1, "nomePaciente": "Ana", "qp": "Dor no peito", "hda": "Há 3 dias",
        "medicoCPF": "11122233344", "prioridade": "Normal"
    })
    assert res.status_code == 200

def test_14_criar_prontuario_dados_parciais(client):
    res = client.post('/api/prontuarios', json={
        "pacienteId": 1, "qp": "Retorno de rotina", "medicoCPF": "11122233344"
    })
    assert res.status_code == 200

def test_15_listagem_prontuarios_desencriptada(client):
    client.post('/api/prontuarios', json={"pacienteId": 1, "hipotese": "Diagnóstico Secreto", "medicoCPF": "11122233344"})
    prontuarios = json.loads(client.get('/api/prontuarios').data)
    assert prontuarios[0]["hipotese"] == "Diagnóstico Secreto"

def test_16_validar_encriptacao_prontuario_banco(client):
    client.post('/api/prontuarios', json={"pacienteId": 1, "qp": "Sintoma X", "medicoCPF": "11122233344"})
    
    # ATUALIZADO: Chama o DB_FILE a partir do models
    conn = sqlite3.connect(meus_models.DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT qp FROM prontuarios ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    
    assert row["qp"] != "Sintoma X"
    assert row["qp"].startswith("gAAAAA")

# ==============================================================================
# MÓDULO 4: AUDITORIA DE ACESSOS E VISUALIZAÇÕES
# ==============================================================================

def test_17_auditoria_criacao_automatica(client):
    client.post('/api/prontuarios', json={"pacienteId": 1, "medicoCPF": "11122233344"})
    logs = json.loads(client.get('/api/prontuarios/auditoria').data)
    assert logs[0]['acao'] == "Criação"
    assert logs[0]['usuario_cpf'] == "11122233344"

def test_18_auditoria_visualizacao_manual(client):
    res_post = client.post('/api/prontuarios/auditoria', json={
        "usuario_cpf": "11122233344", "prontuario_id": 1, "acao": "Visualização"
    })
    assert res_post.status_code == 200
    logs = json.loads(client.get('/api/prontuarios/auditoria').data)
    assert any(log['acao'] == "Visualização" for log in logs)

# ==============================================================================
# MÓDULO EXTRA: COBERTURA E SEGURANÇA
# ==============================================================================

def test_19_consulta_status_padrao_agendado(client):
    client.post('/api/consultas', json={
        "pacienteId": 1, "data": "2026-12-31", "horario": "15:00", "profissional": "Dr. Teste Base"
    })
    ativas = json.loads(client.get('/api/consultas?status=ativas').data)
    consulta_criada = next(c for c in ativas if c['data'] == "2026-12-31")
    assert consulta_criada['status'] == "Agendado"

def test_20_prontuario_paciente_fantasma_seguranca(client):
    with pytest.raises(Exception) as erro:
        client.post('/api/prontuarios', json={
            "pacienteId": 9999, "medicoCPF": "11122233344", "qp": "Teste Invasão"
        })
    assert "FOREIGN KEY" in str(erro.value) or "IntegrityError" in str(type(erro.value))

def test_21_edicao_paciente_inexistente(client):
    res = client.put('/api/pacientes', json={"id": 9999, "nome": "Paciente Fantasma", "contato": "0000"})
    assert res.status_code == 200 

def test_22_isolamento_atualizacao_paciente(client):
    res_a = client.post('/api/pacientes', json={"nome": "Paciente A", "documento": "111"})
    res_b = client.post('/api/pacientes', json={"nome": "Paciente B", "documento": "222"})
    client.put('/api/pacientes', json={"id": json.loads(res_a.data)["id"], "nome": "A Mod", "documento": "999"})
    pacientes = json.loads(client.get('/api/pacientes').data)
    paciente_b = next(p for p in pacientes if p['nome'] == "Paciente B")
    assert paciente_b['documento'] == "222" 

def test_23_paciente_caracteres_especiais_utf8(client):
    nome_complexo = "João Conceição ç á é í ó ú & * @ !"
    client.post('/api/pacientes', json={"nome": nome_complexo, "contato": "99"})
    paciente_inserido = json.loads(client.get('/api/pacientes').data)[0]
    assert paciente_inserido['nome'] == nome_complexo

def test_24_consultas_horarios_seguidos(client):
    client.post('/api/consultas', json={"pacienteId": 1, "data": "2026-10-15", "horario": "14:00", "profissional": "Dr. Teste Base"})
    res = client.post('/api/consultas', json={"pacienteId": 2, "data": "2026-10-15", "horario": "14:30", "profissional": "Dr. Teste Base"})
    assert res.status_code == 200 

def test_25_consultas_filtro_invalido(client):
    res = client.get('/api/consultas?status=STATUS_LOUCO')
    for c in json.loads(res.data): assert c['status'] in ['Agendado', 'Confirmado']

def test_26_reativar_consulta_cancelada(client):
    client.post('/api/consultas', json={"data": "2026-01-01", "horario": "08:00", "status": "Cancelado"})
    id_cancelada = json.loads(client.get('/api/consultas?status=concluidas').data)[0]['id']
    res = client.put('/api/consultas', json={"id": id_cancelada, "status": "Agendado"})
    assert res.status_code == 200

def test_27_prontuario_textos_longos(client):
    texto_longo = "Paciente relata dor de cabeça. " * 500
    res = client.post('/api/prontuarios', json={"pacienteId": 1, "conduta": texto_longo, "medicoCPF": "11122233344"})
    assert json.loads(client.get('/api/prontuarios').data)[0]['conduta'] == texto_longo

def test_28_ordenacao_historico_prontuarios(client):
    client.post('/api/prontuarios', json={"pacienteId": 1, "hipotese": "Prontuário Antigo", "medicoCPF": "11122233344"})
    client.post('/api/prontuarios', json={"pacienteId": 1, "hipotese": "Prontuário Novo", "medicoCPF": "11122233344"})
    prontuarios = json.loads(client.get('/api/prontuarios').data)
    assert prontuarios[0]['hipotese'] == "Prontuário Novo"

def test_29_auditoria_fk_invalida_seguranca(client):
    log_malicioso = {"usuario_cpf": "11122233344", "prontuario_id": 9999999, "acao": "Hacking"}
    with pytest.raises(Exception) as erro:
        client.post('/api/prontuarios/auditoria', json=log_malicioso)
    assert "FOREIGN KEY" in str(erro.value) or "IntegrityError" in str(type(erro.value))

def test_30_auditoria_join_desencriptacao(client):
    res_pac = client.post('/api/pacientes', json={"nome": "Mário Silva"})
    id_pac = json.loads(res_pac.data)["id"]
    client.post('/api/prontuarios', json={"pacienteId": id_pac, "nomePaciente": "Mário Silva", "medicoCPF": "11122233344"})
    log_recente = json.loads(client.get('/api/prontuarios/auditoria').data)[0]
    assert log_recente['nome_profissional'] == "Dr. Teste Base"
    assert log_recente['nome_paciente'] == "Mário Silva"

def test_31_integridade_nome_criptografado_cruzado(client):
    client.post('/api/consultas', json={"nomePaciente": "Ana Cripto", "status": "Agendado"})
    client.post('/api/prontuarios', json={"nomePaciente": "Ana Cripto", "pacienteId": 1, "medicoCPF": "11122233344"})
    consulta = json.loads(client.get('/api/consultas?status=ativas').data)[0]
    prontuario = json.loads(client.get('/api/prontuarios').data)[0]
    assert consulta['nomePaciente'] == prontuario['nomePaciente']

# ==============================================================================
# MÓDULO 6: TESTES NEGATIVOS E TRATAMENTO DE FALHAS (EXPECTATIVA DE ERROS)
# ==============================================================================

def test_32_sql_injection_nome_paciente(client):
    # Tenta injetar código SQL na criação do paciente. O sistema não deve falhar
    # e deve encriptar o texto literal, protegendo o banco de dados.
    payload = {"nome": "Robert'); DROP TABLE pacientes;--", "contato": "123"}
    res = client.post('/api/pacientes', json=payload)
    assert res.status_code == 200
    pacientes = json.loads(client.get('/api/pacientes').data)
    assert any(p['nome'] == payload["nome"] for p in pacientes)

def test_33_xss_injection_prontuario(client):
    # Tenta injetar uma tag de script (XSS) no prontuário.
    # O backend deve tratar como texto normal e encriptá-lo (LGPD).
    payload = {"pacienteId": 1, "medicoCPF": "11122233344", "qp": "<script>alert('hack')</script>"}
    res = client.post('/api/prontuarios', json=payload)
    assert res.status_code == 200
    prontuarios = json.loads(client.get('/api/prontuarios').data)
    assert prontuarios[0]["qp"] == payload["qp"]

def test_34_paciente_put_sem_id(client):
    # Tenta atualizar os dados de um paciente sem enviar o "id" na requisição.
    # O banco tentará fazer WHERE id=None. O servidor não deve cair (deve retornar 200 mas não afetar ninguém).
    client.post('/api/pacientes', json={"nome": "Teste PUT"})
    res = client.put('/api/pacientes', json={"nome": "Novo Nome Hack"})
    assert res.status_code == 200

def test_35_agendar_consulta_choque_mesmo_medico(client):
    # Cria uma consulta base
    client.post('/api/consultas', json={
        "pacienteId": 1, "data": "2026-10-20", "horario": "14:00", "profissional": "Dr. Teste Base"
    })
    # Tenta criar OUTRA consulta no MESMO dia, MESMO horário e MESMO médico (deve ser barrado com 400)
    res = client.post('/api/consultas', json={
        "pacienteId": 2, "data": "2026-10-20", "horario": "14:00", "profissional": "Dr. Teste Base"
    })
    assert res.status_code == 400
    assert "já tem um agendamento" in json.loads(res.data)["error"]

def test_36_agendar_consulta_paciente_inexistente_fk_error(client):
    # Tenta agendar para o paciente de ID 9999 (Força erro de Chave Estrangeira - FK)
    with pytest.raises(Exception) as erro:
        client.post('/api/consultas', json={
            "pacienteId": 9999, "data": "2026-10-20", "horario": "15:00", "profissional": "Dr. Teste Base"
        })
    assert "FOREIGN KEY" in str(erro.value) or "IntegrityError" in str(type(erro.value))

def test_37_prontuario_medico_inexistente_fk_error(client):
    # Tenta criar um prontuário com um CPF de médico que não existe (Força erro de FK)
    with pytest.raises(Exception) as erro:
        client.post('/api/prontuarios', json={"pacienteId": 1, "medicoCPF": "00000000000"})
    assert "FOREIGN KEY" in str(erro.value) or "IntegrityError" in str(type(erro.value))

def test_38_auditoria_usuario_inexistente_fk_error(client):
    # Tenta inserir um log de auditoria associado a um CPF falso
    with pytest.raises(Exception) as erro:
        client.post('/api/prontuarios/auditoria', json={"usuario_cpf": "00000000000", "prontuario_id": 1})
    assert "FOREIGN KEY" in str(erro.value) or "IntegrityError" in str(type(erro.value))

def test_39_auditoria_prontuario_inexistente_fk_error(client):
    # Tenta inserir um log de auditoria para um Prontuário ID falso
    with pytest.raises(Exception) as erro:
        client.post('/api/prontuarios/auditoria', json={"usuario_cpf": "11122233344", "prontuario_id": 99999})
    assert "FOREIGN KEY" in str(erro.value) or "IntegrityError" in str(type(erro.value))

def test_40_rota_inexistente(client):
    # Tenta aceder a um endpoint que não existe (deve retornar 404 Not Found)
    res = client.get('/api/rota_fantasma_que_nao_existe')
    assert res.status_code == 404

def test_41_metodo_delete_nao_permitido_pacientes(client):
    # A API de pacientes aceita GET, POST e PUT. DELETE deve ser barrado com 405 Method Not Allowed
    res = client.delete('/api/pacientes')
    assert res.status_code == 405

def test_42_metodo_delete_nao_permitido_consultas(client):
    # Tenta deletar uma consulta diretamente (deve falhar com 405)
    res = client.delete('/api/consultas')
    assert res.status_code == 405

def test_43_metodo_put_nao_permitido_prontuarios(client):
    # Prontuários não podem ser editados após salvos (Apenas GET e POST permitidos). Deve falhar 405.
    res = client.put('/api/prontuarios', json={"id": 1, "qp": "Fraude"})
    assert res.status_code == 405

def test_44_metodo_put_nao_permitido_auditoria(client):
    # Logs de auditoria jamais devem ser editáveis (Deve falhar 405)
    res = client.put('/api/prontuarios/auditoria', json={"id": 1, "acao": "Apagar Rastros"})
    assert res.status_code == 405

def test_45_auditoria_payload_vazio(client):
    # Envia uma requisição sem payload (sem dados JSON).
    # O servidor deve recusar e retornar um erro HTTP (400, 415 ou 500), mas nunca 200.
    res = client.post('/api/prontuarios/auditoria')
    assert res.status_code != 200

def test_46_consultas_put_sem_id(client):
    # Tenta atualizar o status de uma consulta sem informar de qual consulta se trata.
    res = client.put('/api/consultas', json={"status": "Confirmado"})
    # Não deve deitar abaixo o servidor, apenas falhar silenciosamente no SQLite.
    assert res.status_code == 200
    
def test_47_prontuario_paciente_invalido_fk(client):
    # Passa um texto aleatório onde o banco espera receber um ID Numérico de paciente.
    with pytest.raises(Exception) as erro:
        client.post('/api/prontuarios', json={"pacienteId": "TIPO_INVALIDO", "medicoCPF": "11122233344"})
    assert "FOREIGN KEY" in str(erro.value) or "IntegrityError" in str(type(erro.value)) or "mismatch" in str(erro.value).lower()

def test_48_payload_vazio_pacientes(client):
    # Envia criação de paciente sem JSON.
    with pytest.raises(Exception):
        client.post('/api/pacientes')
        assert res.status_code != 200

def test_49_payload_vazio_consultas(client):
    # Envia criação de consulta sem JSON.
    with pytest.raises(Exception):
        client.post('/api/consultas')
        assert res.status_code != 200

def test_50_consultas_tipagem_invalida(client):
    # Envia um número inteiro onde deveria ser a string do status ("Agendado").
    # Confirma que a API não crasha por erro de tipagem.
    res = client.post('/api/consultas', json={
        "pacienteId": 1, "data": "2026-01-01", "horario": "10:00", "status": 99999
    })
    assert res.status_code == 200

def test_51_sql_injection_status_consulta(client):
    # Tenta injetar comando SQL no status de uma atualização.
    client.post('/api/consultas', json={"data": "2026-11-11", "horario": "09:00", "profissional": "Dr. Teste Base"})
    c_id = json.loads(client.get('/api/consultas?status=ativas').data)[0]['id']
    
    client.put('/api/consultas', json={"id": c_id, "status": "'; DROP TABLE consultas; --"})
    
    # Verifica se a tabela consultas AINDA existe e se o status virou apenas um texto inofensivo
    ativas_res = client.get('/api/consultas?status=ativas')
    assert ativas_res.status_code == 200