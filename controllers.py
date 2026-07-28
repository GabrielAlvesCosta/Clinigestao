from flask import Blueprint, request, jsonify, session
import sqlite3
from datetime import datetime
from models import get_db, en, de

api = Blueprint('api', __name__)

# ==========================================
# ROTAS DE PACIENTES
# ==========================================
@api.route('/pacientes', methods=['GET'])
def get_pacientes():
    with get_db() as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('SELECT * FROM pacientes ORDER BY id DESC').fetchall()
        
        pacientes_descriptografados = []
        for r in rows:
            p = dict(r)
            p['nome'] = de(p.get('nome'))
            p['dataNasc'] = de(p.get('dataNasc'))
            p['genero'] = de(p.get('genero'))
            p['documento'] = de(p.get('documento'))
            p['cartao'] = de(p.get('cartao'))
            p['contato'] = de(p.get('contato'))
            pacientes_descriptografados.append(p)
            
        return jsonify(pacientes_descriptografados)

@api.route('/pacientes', methods=['POST'])
def post_paciente():
    data = request.get_json() or {}
    with get_db() as db:
        cursor = db.execute('''
            INSERT INTO pacientes (nome, dataNasc, genero, documento, cartao, contato)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            en(data.get('nome', 'Sem Nome')),
            en(data.get('dataNasc', '')),
            en(data.get('genero', 'Não informado')),
            en(data.get('documento', '')),
            en(data.get('cartao', '')),
            en(data.get('contato', ''))
        ))
        db.commit()
        return jsonify({"status": "sucesso", "id": cursor.lastrowid}), 201

@api.route('/pacientes', methods=['PUT'])
def put_paciente():
    data = request.get_json() or {}
    with get_db() as db:
        db.execute('''
            UPDATE pacientes SET
                nome=?, dataNasc=?, genero=?, documento=?, cartao=?, contato=?
            WHERE id=?
        ''', (
            en(data.get('nome')), 
            en(data.get('dataNasc')), 
            en(data.get('genero')),
            en(data.get('documento')), 
            en(data.get('cartao')), 
            en(data.get('contato')),
            data.get('id')
        ))
        db.commit()
        return jsonify({"status": "sucesso"}), 200

# ==========================================
# ROTAS DE CONSULTAS
# ==========================================
@api.route('/consultas', methods=['GET'])
def get_consultas():
    status = request.args.get('status', 'ativas')
    with get_db() as db:
        db.row_factory = sqlite3.Row
        query = '''
            SELECT c.*, u.nome as profissional
            FROM consultas c
            LEFT JOIN usuarios u ON c.crm_coren = u.crm_coren
        '''
        if status == 'ativas':
            query += " WHERE c.status NOT IN ('Atendido', 'Cancelado') ORDER BY c.data ASC, c.horario ASC"
        else:
            query += " WHERE c.status IN ('Atendido', 'Cancelado') ORDER BY c.data DESC, c.horario DESC"
            
        rows = db.execute(query).fetchall()
        
        consultas_descriptografadas = []
        for r in rows:
            c = dict(r)
            c['nomePaciente'] = de(c.get('nomePaciente'))
            c['crm_coren'] = de(c.get('crm_coren'))
            consultas_descriptografadas.append(c)
            
        return jsonify(consultas_descriptografadas)

@api.route('/consultas', methods=['POST'])
def post_consulta():
    data = request.get_json() or {}
    paciente_id = data.get('pacienteId')
    crm_coren = data.get('crm_coren')

    if not paciente_id or not crm_coren:
        return jsonify({"error": "Paciente e Profissional (CRM/COREN) são obrigatórios."}), 400

    try:
        with get_db() as db:
            paciente = db.execute('SELECT id FROM pacientes WHERE id = ?', (paciente_id,)).fetchone()
            if not paciente:
                return jsonify({"error": "O paciente selecionado não existe no banco de dados."}), 400

            usuario = None
            rows = db.execute('SELECT crm_coren FROM usuarios').fetchall()
            for row in rows:
                if de(row['crm_coren']) == crm_coren:
                    usuario = row
                    break
            if not usuario:
                return jsonify({"error": f"O profissional com CRM/COREN '{crm_coren}' não está cadastrado no sistema."}), 400

            cursor = db.execute('''
                INSERT INTO consultas (pacienteId, nomePaciente, data, horario, crm_coren, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                paciente_id, 
                en(data.get('nomePaciente')), 
                data.get('data'),
                data.get('horario'), 
                en(crm_coren), 
                data.get('status', 'Agendado')
            ))
            db.commit()
            return jsonify({"status": "sucesso", "id": cursor.lastrowid}), 201

    except Exception as e:
        print(f"Erro ao salvar consulta: {str(e)}")
        return jsonify({"error": f"Erro interno ao agendar consulta: {str(e)}"}), 500

@api.route('/consultas', methods=['PUT'])
def put_consulta():
    data = request.get_json() or {}
    with get_db() as db:
        db.execute("UPDATE consultas SET status=? WHERE id=?", (data.get('status'), data.get('id')))
        db.commit()
        return jsonify({"status": "sucesso"}), 200

# ==========================================
# ROTAS DE PRONTUÁRIOS E AUDITORIA
# ==========================================
@api.route('/prontuarios', methods=['GET'])
def get_prontuarios():
    with get_db() as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('SELECT * FROM prontuarios ORDER BY id DESC').fetchall()
        
        prontuarios_descript = []
        for r in rows:
            p = dict(r)
            # Descriptografar todos os campos sensíveis e clínicos
            p['nomePaciente'] = de(p.get('nomePaciente'))
            p['dataNascimento'] = de(p.get('dataNascimento'))
            p['genero'] = de(p.get('genero'))
            p['documento'] = de(p.get('documento'))
            p['convenioCartao'] = de(p.get('convenioCartao'))
            p['contatoPaciente'] = de(p.get('contatoPaciente'))
            p['acompanhante'] = de(p.get('acompanhante'))
            
            # Dados Clínicos que o usuário solicitou nas imagens
            p['especialidade'] = de(p.get('especialidade'))
            p['tipoAtendimento'] = de(p.get('tipoAtendimento'))
            p['prioridade'] = de(p.get('prioridade'))
            p['sinalPA'] = de(p.get('sinalPA'))
            p['sinalFC'] = de(p.get('sinalFC'))
            p['sinalFR'] = de(p.get('sinalFR'))
            p['sinalTEMP'] = de(p.get('sinalTEMP'))
            p['sinalSATO2'] = de(p.get('sinalSATO2'))
            p['peso'] = de(p.get('peso'))
            p['altura'] = de(p.get('altura'))
            p['estadoGeral'] = de(p.get('estadoGeral'))
            p['cardioResp'] = de(p.get('cardioResp'))
            p['neuroOutros'] = de(p.get('neuroOutros'))
            
            # Histórico e Hipóteses
            p['qp'] = de(p.get('qp'))
            p['hda'] = de(p.get('hda'))
            p['hmp'] = de(p.get('hmp'))
            p['alergias'] = de(p.get('alergias'))
            p['hipotese'] = de(p.get('hipotese'))
            p['conduta'] = de(p.get('conduta'))
            p['crm_coren'] = de(p.get('crm_coren'))
            p['registroProfissional'] = de(p.get('registroProfissional'))
            p['carimboAssinatura'] = de(p.get('carimboAssinatura'))
            prontuarios_descript.append(p)
            
        return jsonify(prontuarios_descript)

@api.route('/prontuarios', methods=['POST'])
def post_prontuario():
    data = request.get_json() or {}
    try:
        with get_db() as db:
            usuario_sessao = session.get('usuario', {})
            crm_coren_logado = usuario_sessao.get('crm_coren') or data.get('crm_coren', 'S/N')
            nome_profissional = usuario_sessao.get('nome', 'Profissional')
            
            carimbo_enviado = data.get('carimboAssinatura')
            carimbo_sessao = usuario_sessao.get('assinatura')
            assinatura_final = carimbo_enviado if (carimbo_enviado and carimbo_enviado.strip() != '') else (carimbo_sessao or '')
            crm_coren_encrypted = en(crm_coren_logado)
            assinatura_final_encrypted = en(assinatura_final)

            cursor = db.execute('''
                INSERT INTO prontuarios (
                    pacienteId, nomePaciente, dataNascimento, genero,
                    documento, convenioCartao, contatoPaciente, acompanhante, especialidade, tipoAtendimento,
                    prioridade, qp, hda, hmp, alergias, sinalPA, sinalFC, sinalFR, sinalTEMP, sinalSATO2, peso, altura,
                    estadoGeral, cardioResp, neuroOutros, hipotese, conduta, crm_coren, registroProfissional, carimboAssinatura
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('pacienteId'), 
                en(data.get('nomePaciente')), 
                en(data.get('dataNascimento')), 
                en(data.get('genero')),
                en(data.get('documento')), 
                en(data.get('convenioCartao')), 
                en(data.get('contatoPaciente')), 
                en(data.get('acompanhante')), 
                en(data.get('especialidade')),
                en(data.get('tipoAtendimento')), 
                en(data.get('prioridade')), 
                en(data.get('qp')), 
                en(data.get('hda')),
                en(data.get('hmp')), 
                en(data.get('alergias')), 
                en(data.get('sinalPA')), 
                en(data.get('sinalFC')),
                en(data.get('sinalFR')), 
                en(data.get('sinalTEMP')), 
                en(data.get('sinalSATO2')), 
                en(data.get('peso')),
                en(data.get('altura')),
                en(data.get('estadoGeral')),
                en(data.get('cardioResp')), 
                en(data.get('neuroOutros')), 
                en(data.get('hipotese')), 
                en(data.get('conduta')),
                crm_coren_encrypted, 
                crm_coren_encrypted, 
                assinatura_final_encrypted
            ))
            
            prontuario_id = cursor.lastrowid

            data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            db.execute('''
                INSERT INTO auditoria (data_hora, nome_profissional, crm_coren, acao, prontuario_id, nome_paciente)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data_hora_atual,
                nome_profissional,
                crm_coren_encrypted,
                'Criação',
                prontuario_id,
                en(data.get('nomePaciente', 'N/A'))
            ))

            db.commit()
            return jsonify({"status": "sucesso", "id": prontuario_id}), 201

    except Exception as e:
        print(f"Erro Crítico ao salvar prontuário: {str(e)}")
        return jsonify({"error": f"Erro interno no servidor: {str(e)}"}), 500

@api.route('/prontuarios/<int:id>', methods=['GET'])
def get_prontuario_por_id(id):
    try:
        with get_db() as db:
            db.row_factory = sqlite3.Row
            prontuario_row = db.execute('SELECT * FROM prontuarios WHERE id = ?', (id,)).fetchone()
            
            if not prontuario_row:
                return jsonify({"error": "Prontuário não encontrado"}), 404
            
            # Descriptografar o prontuário unitário
            prontuario = dict(prontuario_row)
            prontuario['nomePaciente'] = de(prontuario.get('nomePaciente'))
            prontuario['dataNascimento'] = de(prontuario.get('dataNascimento'))
            prontuario['genero'] = de(prontuario.get('genero'))
            prontuario['documento'] = de(prontuario.get('documento'))
            prontuario['convenioCartao'] = de(prontuario.get('convenioCartao'))
            prontuario['contatoPaciente'] = de(prontuario.get('contatoPaciente'))
            prontuario['acompanhante'] = de(prontuario.get('acompanhante'))
            
            # Dados Clínicos
            prontuario['especialidade'] = de(prontuario.get('especialidade'))
            prontuario['tipoAtendimento'] = de(prontuario.get('tipoAtendimento'))
            prontuario['prioridade'] = de(prontuario.get('prioridade'))
            prontuario['sinalPA'] = de(prontuario.get('sinalPA'))
            prontuario['sinalFC'] = de(prontuario.get('sinalFC'))
            prontuario['sinalFR'] = de(prontuario.get('sinalFR'))
            prontuario['sinalTEMP'] = de(prontuario.get('sinalTEMP'))
            prontuario['sinalSATO2'] = de(prontuario.get('sinalSATO2'))
            prontuario['peso'] = de(prontuario.get('peso'))
            prontuario['altura'] = de(prontuario.get('altura'))
            prontuario['estadoGeral'] = de(prontuario.get('estadoGeral'))
            prontuario['cardioResp'] = de(prontuario.get('cardioResp'))
            prontuario['neuroOutros'] = de(prontuario.get('neuroOutros'))
            
            # Histórico e Hipóteses
            prontuario['qp'] = de(prontuario.get('qp'))
            prontuario['hda'] = de(prontuario.get('hda'))
            prontuario['hmp'] = de(prontuario.get('hmp'))
            prontuario['alergias'] = de(prontuario.get('alergias'))
            prontuario['hipotese'] = de(prontuario.get('hipotese'))
            prontuario['conduta'] = de(prontuario.get('conduta'))
            prontuario['crm_coren'] = de(prontuario.get('crm_coren'))
            prontuario['registroProfissional'] = de(prontuario.get('registroProfissional'))
            prontuario['carimboAssinatura'] = de(prontuario.get('carimboAssinatura'))
            
            usuario_sessao = session.get('usuario', {})
            nome_prof = usuario_sessao.get('nome', 'Profissional')
            crm_logado = usuario_sessao.get('crm_coren', 'N/A')
            data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            db.execute('''
                INSERT INTO auditoria (data_hora, nome_profissional, crm_coren, acao, prontuario_id, nome_paciente)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data_hora_atual,
                nome_prof,
                crm_logado,
                'Visualização',
                id,
                en(prontuario['nomePaciente'])
            ))
            db.commit()
            
            return jsonify(prontuario), 200

    except Exception as e:
        print(f"Erro ao visualizar prontuário: {str(e)}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@api.route('/prontuarios/auditoria', methods=['GET'])
def get_auditoria():
    with get_db() as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('SELECT * FROM auditoria ORDER BY id DESC').fetchall()
        
        auditoria_descript = []
        for r in rows:
            l = dict(r)
            l['nome_paciente'] = de(l.get('nome_paciente'))
            l['crm_coren'] = de(l.get('crm_coren'))
            auditoria_descript.append(l)
            
        return jsonify(auditoria_descript)

@api.route('/prontuarios/auditoria', methods=['POST'])
def post_auditoria():
    data = request.get_json() or {}
    with get_db() as db:
        data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        usuario_sessao = session.get('usuario', {})
        nome_prof = usuario_sessao.get('nome', 'Profissional')
        crm_logado = usuario_sessao.get('crm_coren', 'N/A')
        crm_encrypted = en(crm_logado)
        
        db.execute('''
            INSERT INTO auditoria (data_hora, nome_profissional, crm_coren, acao, prontuario_id, nome_paciente)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data_hora_atual,
            nome_prof,
            en(data.get('crm_coren', crm_logado)),
            data.get('acao', 'Visualização'),
            data.get('prontuario_id'),
            en(data.get('nome_paciente', 'N/A'))
        ))
        db.commit()
        return jsonify({"status": "sucesso"}), 201

@api.route('/usuarios', methods=['GET'])
def get_usuarios():
    try:
        with get_db() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute('SELECT * FROM usuarios').fetchall()
            usuarios = []
            for r in rows:
                usuario = dict(r)
                usuario['crm_coren'] = de(usuario.get('crm_coren'))
                usuario['assinatura'] = de(usuario.get('assinatura'))
                usuarios.append(usuario)
            return jsonify(usuarios)
            
    except Exception as e:
        print(f"Erro ao buscar usuários: {e}")
        if "usuario" in session:
            return jsonify([session["usuario"]])
        return jsonify([])