function obterNomeProfissionalLogado() {
    return window.usuarioLogado ? window.usuarioLogado.nome : '';
}

function obterCRMCORENProfissionalLogado() {
    return window.usuarioLogado ? window.usuarioLogado.crm_coren : '';
}

function obterCarimboProfissionalLogado() {
    if (!window.usuarioLogado) return '';
    return window.usuarioLogado.assinatura || window.usuarioLogado.foto || window.usuarioLogado.carimboAssinatura || '';
}

function obterUrlCarimboValida(carimbo) {
    if (!carimbo || carimbo === 'null' || carimbo === 'undefined' || typeof carimbo !== 'string') return '';
    
    let trimVal = carimbo.trim();
    if (!trimVal) return '';

    if (trimVal.startsWith('/static/')) return trimVal;

    if (trimVal.startsWith('data:') || trimVal.startsWith('http://') || trimVal.startsWith('https://')) {
        return trimVal;
    }

    let caminhoLimpo = trimVal.replace(/\\/g, '/');

    let nomeArquivo = caminhoLimpo.split('/').pop();
    if (!nomeArquivo) return '';
    
    return `/static/uploads/${nomeArquivo}`;
}

function previewCarimbo(input) {
    const preview = document.getElementById('prontuarioCarimboPreview');
    if (preview && input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.classList.remove('d-none');
        };
        reader.readAsDataURL(input.files[0]);
    } else if (preview) {
        preview.src = "";
        preview.classList.add('d-none');
    }
}

function previewFoto(input) {
    const perfilFoto = document.getElementById('perfilFoto');
    if (perfilFoto && input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) { perfilFoto.src = e.target.result; };
        reader.readAsDataURL(input.files[0]);
    }
}

function carregarDadosPerfil() {
    const cpfLogado = localStorage.getItem('loggedInUserCPF');
    if (cpfLogado) {
        const dados = localStorage.getItem(cpfLogado);
        if (dados) {
            try {
                const user = JSON.parse(dados);
                const display = document.getElementById('user-display-name');
                if (display) display.textContent = user.nome ? "Profissional: " + user.nome.split(' ')[0] : 'Profissional';
                if (document.getElementById('perfilNome')) document.getElementById('perfilNome').value = user.nome || '';
                if (document.getElementById('perfilEmail')) document.getElementById('perfilEmail').value = user.email || '';
                if (document.getElementById('perfilCPF')) document.getElementById('perfilCPF').value = user.cpf || '';
                
                if (document.getElementById('perfilFoto') && user.foto) {
                    document.getElementById('perfilFoto').src = obterUrlCarimboValida(user.foto);
                }
            } catch(e) {
                console.error("Erro ao carregar dados do perfil:", e);
            }
        }
    }
}

async function salvarPerfil() {
    const cpfLogado = localStorage.getItem('loggedInUserCPF');
    if (!cpfLogado) return alert("Erro de sessão do profissional.");

    let user = {};
    const dados = localStorage.getItem(cpfLogado);
    if (dados) { 
        try { user = JSON.parse(dados); } catch(e){} 
    }

    user.nome = document.getElementById('perfilNome')?.value || '';
    user.email = document.getElementById('perfilEmail')?.value || '';
    user.foto = document.getElementById('perfilFoto')?.src || '';

    localStorage.setItem(cpfLogado, JSON.stringify(user));
    
    try {
        await fetch('/api/usuarios', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(user)
        });
    } catch(e) {
        console.error("Erro ao salvar perfil no servidor:", e);
    }

    carregarDadosPerfil();
    await atualizarDropdownProfissionais();
    await renderizarMinhasConsultas();
    await renderizarMinhasConsultasConcluidas();

    alert("Dados salvos e atualizados com sucesso!");
}

async function atualizarDropdownPacientes() {
    const selectProntuario = document.getElementById('prontuarioPacienteSelect');
    const selectConsulta = document.getElementById('consultaPacienteSelect');
    if (!selectProntuario && !selectConsulta) return;

    try {
        const res = await fetch('/api/pacientes');
        if (!res.ok) return;
        const pacientes = await res.json();
        
        const optionsHTML = '<option value="">Selecione um paciente cadastrado...</option>' + 
            pacientes.map(p => `<option value="${p.id}" data-doc="${p.documento || ''}">${p.nome || 'Sem Nome'} (Doc: ${p.documento || 'S/N'})</option>`).join('');

        if (selectProntuario) selectProntuario.innerHTML = optionsHTML;
        if (selectConsulta) selectConsulta.innerHTML = optionsHTML;
    } catch(e) {
        console.error("Erro ao atualizar dropdown de pacientes:", e);
    }
}

async function atualizarDropdownProfissionais() {
    const selectProfissional = document.getElementById('consultaProfissional');
    if (!selectProfissional) return;

    try {
        const res = await fetch('/api/usuarios');
        if (!res.ok) throw new Error("Erro na requisição da API");

        const usuarios = await res.json();
        
        const apenasMedicos = usuarios.filter(u => {
            const cargoDoUsuario = (u.admin || '').toLowerCase();
            return cargoDoUsuario == 'comum';
        });

        const optionsHTML = '<option value="">Selecione o Médico / Especialista...</option>' + 
            apenasMedicos.map(u => {
                const nome = u.nome || u.username || 'Profissional Desconhecido';
                return `<option value="${u.crm_coren}">${nome} (${u.crm_coren || 'S/N'})</option>`;
            }).join('');

        selectProfissional.innerHTML = optionsHTML;
    } catch(e) {
        console.error("Erro ao atualizar dropdown de profissionais:", e);
    }
}

async function cadastrarPaciente(event) {
    if (event) event.preventDefault();

    const btnSubmit = document.querySelector('#formNovoPaciente button[type="submit"]');
    if (btnSubmit) {
        if (btnSubmit.disabled) return;
        btnSubmit.disabled = true;
        btnSubmit.dataset.texto = btnSubmit.innerHTML;
        btnSubmit.innerHTML = 'Salvando...';
    }

    const radioGenero = document.querySelector('input[name="pacienteGenero"]:checked');
    const generoSelecionado = radioGenero ? radioGenero.value : "Não informado";
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';

    const dataNascVal = getVal('pacienteDataNasc');
    const hojeData = new Date().toISOString().split('T')[0];
    
    if (dataNascVal > hojeData) {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = btnSubmit.dataset.texto;
        }
        return alert("A data de nascimento não pode ser no futuro!");
    }

    const novoPaciente = {
        nome: getVal('pacienteNome'),
        dataNasc: dataNascVal,
        genero: generoSelecionado,
        documento: getVal('pacienteDocumento'),
        cartao: getVal('pacienteCartao'),
        contato: getVal('pacienteContato')
    };

    try {
        const res = await fetch('/api/pacientes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(novoPaciente)
        });

        if (res.ok) {
            alert("Paciente cadastrado com sucesso!");
            const form = document.getElementById('formNovoPaciente');
            if (form) form.reset();
            
            await atualizarDropdownPacientes();
            await renderizarTabelaPacientes();

            const tab = document.getElementById('tab-pacientes-cadastrados');
            if (tab && typeof bootstrap !== 'undefined') {
                bootstrap.Tab.getOrCreateInstance(tab).show();
            }
        } else {
            alert("Falha ao salvar paciente no servidor.");
        }
    } catch(e) { 
        console.error("Erro ao cadastrar paciente:", e);
        alert("Erro ao cadastrar o paciente."); 
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = btnSubmit.dataset.texto;
        }
    }
}

async function renderizarTabelaPacientes() {
    const tabela = document.getElementById('tabelaPacientes');
    if (!tabela) return;

    try {
        const res = await fetch('/api/pacientes');
        if (!res.ok) throw new Error(`Status do servidor: ${res.status}`);
        
        const pacientes = await res.json();
        const inputBusca = document.getElementById('buscaPacienteLista');
        const termoBusca = inputBusca ? inputBusca.value.toLowerCase().trim() : '';

        tabela.innerHTML = '';

        const filtrados = pacientes.filter(p => (p.nome || '').toLowerCase().includes(termoBusca) || (p.documento || '').toLowerCase().includes(termoBusca));

        if (filtrados.length === 0) {
            tabela.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">Nenhum paciente localizado.</td></tr>`;
            return;
        }

        filtrados.forEach(p => {
            tabela.insertAdjacentHTML('beforeend', `
                <tr>
                    <td><strong class="text-dark">${p.nome || 'Sem Nome'}</strong></td>
                    <td>${formatarDataBR(p.dataNasc)} / <span class="text-muted">${p.genero || 'N/I'}</span></td>
                    <td>${p.documento || 'Não informado'}</td>
                    <td>${p.cartao || 'Não informado'}</td>
                    <td>${p.contato || 'Não informado'}</td>
                    <td class="text-end text-nowrap">
                        <button class="btn btn-sm btn-outline-primary" onclick="abrirEdicaoPaciente(${p.id})">
                            <i class="bi bi-pencil-square"></i> Editar
                        </button>
                    </td>
                </tr>
            `);
        });
    } catch(e) {
        console.error("Erro ao renderizar tabela de pacientes:", e);
    }
}

async function abrirEdicaoPaciente(id) {
    try {
        const res = await fetch('/api/pacientes');
        const pacientes = await res.json();
        const paciente = pacientes.find(p => p.id == id);
        if (!paciente) return alert("Paciente não localizado.");

        const setVal = (id, val) => { if (document.getElementById(id)) document.getElementById(id).value = val || ''; };

        setVal('editPacienteId', paciente.id);
        setVal('editPacienteNome', paciente.nome);
        setVal('editPacienteDataNasc', paciente.dataNasc);
        setVal('editPacienteGenero', paciente.genero || 'Masculino');
        setVal('editPacienteDocumento', paciente.documento);
        setVal('editPacienteCartao', paciente.cartao);
        setVal('editPacienteContato', paciente.contato);

        const modalEl = document.getElementById('modalEditarPaciente');
        if (modalEl && typeof bootstrap !== 'undefined') {
            bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }
    } catch(e) {
        console.error("Erro ao abrir edição de paciente:", e);
    }
}

async function salvarEdicaoPaciente() {
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';

    const id = parseInt(getVal('editPacienteId'));
    const dataNascVal = getVal('editPacienteDataNasc');
    const hojeData = new Date().toISOString().split('T')[0];

    if (dataNascVal > hojeData) {
        return alert("A data de nascimento não pode ser no futuro!");
    }

    const pacienteAtualizado = {
        id: id,
        nome: getVal('editPacienteNome'),
        dataNasc: dataNascVal,
        genero: getVal('editPacienteGenero'),
        documento: getVal('editPacienteDocumento'),
        cartao: getVal('editPacienteCartao'),
        contato: getVal('editPacienteContato')
    };

    try {
        const res = await fetch('/api/pacientes', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pacienteAtualizado)
        });
        if (res.ok) {
            await atualizarDropdownPacientes();
            await renderizarTabelaPacientes();
            const modalEl = document.getElementById('modalEditarPaciente');
            if (modalEl) bootstrap.Modal.getInstance(modalEl)?.hide();
            alert("Dados cadastrais do paciente atualizados!");
        }
    } catch(e) {
        console.error("Erro ao salvar edição de paciente:", e);
    }
}

async function agendarConsulta(event) {
    if (event) event.preventDefault();

    try {
        const pacienteId = parseInt(document.getElementById('consultaPacienteSelect')?.value);
        if (!pacienteId) return alert("Por favor, selecione um paciente.");

        const dataInput = document.getElementById('consultaData')?.value;
        const horarioInput = document.getElementById('consultaHorario')?.value;
        const profissionalInput = document.getElementById('consultaProfissional')?.value;

        if (!dataInput || !horarioInput) return alert("Por favor, selecione a data e o horário da consulta.");
        if (!profissionalInput) return alert("Por favor, selecione o médico / especialista responsável.");

        const dataHoraConsulta = new Date(`${dataInput}T${horarioInput}`);
        const agora = new Date();

        if (dataHoraConsulta < agora) {
            return alert("Erro crítico: Não é possível agendar uma consulta para uma data ou horário que já passou!");
        }

        const resConsultasAtivas = await fetch('/api/consultas?status=ativas');
        if (resConsultasAtivas.ok) {
            const consultasAtivas = await resConsultasAtivas.json();
            const conflito = consultasAtivas.find(c => 
                (c.crm_coren === profissionalInput || c.profissional === profissionalInput) &&
                c.data === dataInput &&
                c.horario === horarioInput
            );

            if (conflito) {
                return alert("Horário indisponível! Este profissional já possui uma consulta agendada para essa mesma data e horário.");
            }
        }

        const btnSubmit = document.querySelector('#formNovaConsulta button[type="submit"]');
        if (btnSubmit) {
            if (btnSubmit.disabled) return;
            btnSubmit.disabled = true;
            btnSubmit.dataset.texto = btnSubmit.innerHTML;
            btnSubmit.innerHTML = 'Agendando...';
        }

        const selectPac = document.getElementById('consultaPacienteSelect');
        const selectedOption = selectPac.options[selectPac.selectedIndex];
        const nomePaciente = selectedOption.text.split(' (Doc:')[0];
        const documentoPaciente = selectedOption.dataset.doc || '';

        const novaConsulta = {
            pacienteId: pacienteId,
            documento: documentoPaciente,
            nomePaciente: nomePaciente,
            data: dataInput,
            horario: horarioInput,
            crm_coren: profissionalInput,
            status: 'Agendado'
        };

        const response = await fetch('/api/consultas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(novaConsulta)
        });

        if (!response.ok) {
            const errData = await response.json();
            if (btnSubmit) {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = btnSubmit.dataset.texto;
            }
            return alert(errData.error || `Erro ao agendar consulta. Status do Servidor: ${response.status}`);
        }

        alert("Consulta agendada com sucesso!");
        const form = document.getElementById('formNovaConsulta');
        if (form) form.reset();
        
        await renderizarTabelaConsultas();
        await renderizarTabelaConsultasConcluidas();
        await renderizarMinhasConsultas();
        await renderizarMinhasConsultasConcluidas();
        await atualizarPainelAtendimentos();

        const tab = document.getElementById('tab-consultas-agendadas');
        if (tab && typeof bootstrap !== 'undefined') {
            bootstrap.Tab.getOrCreateInstance(tab).show();
        }

        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = btnSubmit.dataset.texto;
        }

    } catch (error) {
        console.error("Erro crítico e inesperado ao agendar consulta:", error);
        alert("Ocorreu uma falha no sistema. Por favor, verifique o Console (F12) para mais detalhes.");
        
        const btnSubmit = document.querySelector('#formNovaConsulta button[type="submit"]');
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = btnSubmit.dataset.texto;
        }
    }
}

function obterClasseStatusConsulta(status) {
    if (status === 'Confirmado') return 'bg-success text-white';
    if (status === 'Cancelado') return 'bg-danger text-white';
    if (status === 'Atendido') return 'bg-info text-dark';
    return 'bg-primary text-white';
}

async function renderizarTabelaConsultas() {
    const tabela = document.getElementById('tabelaConsultas');
    if (!tabela) return;

    try {
        const res = await fetch('/api/consultas?status=ativas');
        if (!res.ok) return;
        const consultas = await res.json();
        
        const inputBusca = document.getElementById('buscaConsulta');
        const termoBusca = inputBusca ? inputBusca.value.toLowerCase().trim() : '';

        tabela.innerHTML = '';

        const filtradas = consultas.filter(c => {
            const pac = (c.nomePaciente || '').toLowerCase();
            const doc = (c.documento || '').toLowerCase();
            const med = (c.profissional || '').toLowerCase();
            return pac.includes(termoBusca) || doc.includes(termoBusca) || med.includes(termoBusca);
        });

        if (filtradas.length === 0) {
            tabela.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">Nenhuma consulta ativa agendada.</td></tr>`;
            return;
        }

        filtradas.forEach(c => {
            tabela.insertAdjacentHTML('beforeend', `
                <tr>
                    <td>
                        <strong class="text-dark">${c.nomePaciente || 'Sem Nome'}</strong>
                        ${c.documento ? `<br><small class="text-muted" style="font-size: 0.85em;">Doc: ${c.documento}</small>` : ''}
                    </td>
                    <td><i class="bi bi-calendar3 text-primary"></i> ${formatarDataBR(c.data)} às <strong>${c.horario}</strong></td>
                    <td><span class="badge bg-secondary">${c.profissional} (${c.crm_coren || 'S/N'})</span></td>
                    <td><span class="badge ${obterClasseStatusConsulta(c.status)}">${c.status}</span></td>
                    <td class="text-end text-nowrap">
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-success" onclick="alterarStatusConsulta(${c.id}, 'Confirmado')" title="Confirmar Presença"><i class="bi bi-check-lg"></i></button>
                            <button class="btn btn-outline-info" onclick="alterarStatusConsulta(${c.id}, 'Atendido')" title="Finalizar Atendimento"><i class="bi bi-person-check"></i></button>
                            <button class="btn btn-outline-danger" onclick="alterarStatusConsulta(${c.id}, 'Cancelado')" title="Cancelar Horário"><i class="bi bi-x-lg"></i></button>
                        </div>
                    </td>
                </tr>
            `);
        });
    } catch(e) {
        console.error("Erro ao renderizar tabela de consultas:", e);
    }
}

async function renderizarTabelaConsultasConcluidas() {
    const tabela = document.getElementById('tabelaConsultasConcluidas');
    if (!tabela) return;

    try {
        const res = await fetch('/api/consultas?status=concluidas');
        if (!res.ok) return;
        const consultas = await res.json();
        
        const inputBusca = document.getElementById('buscaConsultaConcluida');
        const termoBusca = inputBusca ? inputBusca.value.toLowerCase().trim() : '';

        tabela.innerHTML = '';

        const filtradas = consultas.filter(c => {
            const pac = (c.nomePaciente || '').toLowerCase();
            const doc = (c.documento || '').toLowerCase();
            const med = (c.profissional || '').toLowerCase();
            return pac.includes(termoBusca) || doc.includes(termoBusca) || med.includes(termoBusca);
        });

        if (filtradas.length === 0) {
            tabela.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">Nenhuma consulta finalizada ou cancelada localizada.</td></tr>`;
            return;
        }

        filtradas.forEach(c => {
            tabela.insertAdjacentHTML('beforeend', `
                <tr>
                    <td>
                        <strong class="text-dark">${c.nomePaciente || 'Sem Nome'}</strong>
                        ${c.documento ? `<br><small class="text-muted" style="font-size: 0.85em;">Doc: ${c.documento}</small>` : ''}
                    </td>
                    <td><i class="bi bi-calendar-check text-secondary"></i> ${formatarDataBR(c.data)} às <strong>${c.horario}</strong></td>
                    <td><span class="badge bg-secondary">${c.profissional} (${c.crm_coren || 'S/N'})</span></td>
                    <td><span class="badge ${obterClasseStatusConsulta(c.status)}">${c.status}</span></td>
                    <td class="text-end text-nowrap">
                        <button class="btn btn-sm btn-outline-secondary" onclick="alterarStatusConsulta(${c.id}, 'Agendado')" title="Reativar para o Mural"><i class="bi bi-arrow-counterclockwise"></i> Reativar</button>
                    </td>
                </tr>
            `);
        });
    } catch(e) {
        console.error("Erro ao renderizar consultas concluídas:", e);
    }
}

async function renderizarMinhasConsultas() {
    const tabela = document.getElementById('tabelaMinhasConsultas');
    if (!tabela) return;

    const meuCrm = obterCRMCORENProfissionalLogado();
    if (!meuCrm) return;

    try {
        const res = await fetch('/api/consultas?status=ativas');
        if (!res.ok) return;
        
        const todasAtivas = await res.json();
        const minhasAtivas = todasAtivas.filter(c => c.crm_coren === meuCrm);

        tabela.innerHTML = '';
        if (minhasAtivas.length === 0) {
            tabela.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-4">Você não possui agendamentos pendentes.</td></tr>`;
            return;
        }

        minhasAtivas.forEach(c => {
            tabela.insertAdjacentHTML('beforeend', `
                <tr>
                    <td>
                        <strong class="text-dark">${c.nomePaciente || 'Sem Nome'}</strong>
                        ${c.documento ? `<br><small class="text-muted" style="font-size: 0.85em;">Doc: ${c.documento}</small>` : ''}
                    </td>
                    <td><i class="bi bi-calendar3 text-primary"></i> ${formatarDataBR(c.data)}<br><strong>${c.horario}</strong></td>
                    <td><span class="badge ${obterClasseStatusConsulta(c.status)}">${c.status}</span></td>
                    <td class="text-end text-nowrap">
                        <div class="btn-group btn-group-sm d-flex flex-column gap-1">
                            <button class="btn btn-outline-success" onclick="alterarStatusConsulta(${c.id}, 'Confirmado')" title="Confirmar"><i class="bi bi-check-lg"></i></button>
                            <button class="btn btn-outline-info" onclick="alterarStatusConsulta(${c.id}, 'Atendido')" title="Finalizar"><i class="bi bi-person-check"></i></button>
                            <button class="btn btn-outline-danger" onclick="alterarStatusConsulta(${c.id}, 'Cancelado')" title="Cancelar"><i class="bi bi-x-lg"></i></button>
                        </div>
                    </td>
                </tr>
            `);
        });
    } catch(e) {
        console.error("Erro ao renderizar minhas consultas:", e);
    }
}

async function renderizarMinhasConsultasConcluidas() {
    const tabela = document.getElementById('tabelaMinhasConsultasConcluidas');
    if (!tabela) return;

    const meuCrm = obterCRMCORENProfissionalLogado();
    if (!meuCrm) return;

    try {
        const res = await fetch('/api/consultas?status=concluidas');
        if (!res.ok) return;
        
        const todasConcluidas = await res.json();
        const minhasConcluidas = todasConcluidas.filter(c => c.crm_coren === meuCrm);

        tabela.innerHTML = '';
        if (minhasConcluidas.length === 0) {
            tabela.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-4">Você não possui histórico concluído.</td></tr>`;
            return;
        }

        minhasConcluidas.forEach(c => {
            tabela.insertAdjacentHTML('beforeend', `
                <tr>
                    <td>
                        <strong class="text-dark">${c.nomePaciente || 'Sem Nome'}</strong>
                        ${c.documento ? `<br><small class="text-muted" style="font-size: 0.85em;">Doc: ${c.documento}</small>` : ''}
                    </td>
                    <td><i class="bi bi-calendar-check text-secondary"></i> ${formatarDataBR(c.data)}<br><strong>${c.horario}</strong></td>
                    <td><span class="badge ${obterClasseStatusConsulta(c.status)}">${c.status}</span></td>
                    <td class="text-end text-nowrap">
                        <button class="btn btn-sm btn-outline-secondary" onclick="alterarStatusConsulta(${c.id}, 'Agendado')" title="Reativar"><i class="bi bi-arrow-counterclockwise"></i></button>
                    </td>
                </tr>
            `);
        });
    } catch(e) {
        console.error("Erro ao renderizar minhas consultas concluídas:", e);
    }
}

async function atualizarPainelAtendimentos() {
    try {
        const resAtivas = await fetch('/api/consultas?status=ativas');
        const ativas = await resAtivas.json();

        const resConcluidas = await fetch('/api/consultas?status=concluidas');
        const concluidas = await resConcluidas.json();

        const resProntuarios = await fetch('/api/prontuarios');
        const prontuarios = await resProntuarios.json();

        const crmLogado = obterCRMCORENProfissionalLogado();

        const ativasDoProfissional = ativas.filter(c => c.crm_coren === crmLogado);
        const concluidasDoProfissional = concluidas.filter(c => c.crm_coren === crmLogado);
        const prontuariosDoProfissional = prontuarios.filter(p => p.crm_coren === crmLogado);

        if (document.getElementById('count-consultas-ativas')) document.getElementById('count-consultas-ativas').textContent = ativasDoProfissional.length;
        if (document.getElementById('count-consultas-concluidas')) document.getElementById('count-consultas-concluidas').textContent = concluidasDoProfissional.length;
        if (document.getElementById('count-prontuarios')) document.getElementById('count-prontuarios').textContent = prontuariosDoProfissional.length;
    } catch(e) {
        console.error("Erro ao atualizar painel:", e);
    }
}

async function alterarStatusConsulta(id, novoStatus) {
    try {
        const res = await fetch('/api/consultas', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, status: novoStatus })
        });
        if (res.ok) {
            await renderizarTabelaConsultas();
            await renderizarTabelaConsultasConcluidas();
            await renderizarMinhasConsultas();
            await renderizarMinhasConsultasConcluidas();
            await atualizarPainelAtendimentos();
        }
    } catch(e) {
        console.error("Erro ao alterar status da consulta:", e);
    }
}

async function publicarProntuario(event) {
    if (event) event.preventDefault();

    const selectPaciente = document.getElementById('prontuarioPacienteSelect');
    const pacienteId = selectPaciente ? selectPaciente.value : '';
    
    if (!pacienteId) {
        alert("Por favor, selecione um paciente para registrar o prontuário.");
        return;
    }

    const btnSubmit = document.querySelector('#formNovoProntuario button[type="submit"]');
    if (btnSubmit) {
        if (btnSubmit.disabled) return;
        btnSubmit.disabled = true;
        btnSubmit.dataset.texto = btnSubmit.innerHTML;
        btnSubmit.innerHTML = 'Publicando...';
    }

    try {
        const pRes = await fetch('/api/pacientes');
        if (!pRes.ok) throw new Error("Não foi possível validar o paciente no servidor.");
        
        const pacientes = await pRes.json();
        const paciente = pacientes.find(p => p.id == pacienteId);

        if (!paciente) {
            alert("Erro: O paciente selecionado não foi encontrado na base de dados.");
            return;
        }

        const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';

        const previewEl = document.getElementById('prontuarioCarimboPreview');
        let carimboImg = (previewEl && !previewEl.classList.contains('d-none')) ? previewEl.src : '';

        if (!carimboImg) {
            carimboImg = obterCarimboProfissionalLogado();
        }

        console.log("📸 Imagem do Carimbo capturada:", {
            veioDoPreview: previewEl ? previewEl.src : null,
            previewEstaVisivel: previewEl ? !previewEl.classList.contains('d-none') : false,
            veioDoPerfil: obterCarimboProfissionalLogado(),
            resultadoFinal: carimboImg
        });

        const novoProntuario = {
            pacienteId: paciente.id,
            nomePaciente: paciente.nome,
            dataNascimento: paciente.dataNasc,
            genero: paciente.genero,
            documento: paciente.documento,
            convenioCartao: paciente.cartao,
            contatoPaciente: paciente.contato || 'Não cadastrado', 
            acompanhante: getVal('prontuarioAcompanhante'),
            especialidade: getVal('prontuarioEspecialidade'),
            tipoAtendimento: getVal('prontuarioTipoAtendimento'),
            prioridade: getVal('prontuarioPrioridade'),
            qp: getVal('prontuarioQP'),
            hda: getVal('prontuarioHDA'),
            hmp: getVal('prontuarioHMP'),
            alergias: getVal('prontuarioAlergias'),
            sinalPA: getVal('prontuarioPA'),
            sinalFC: getVal('prontuarioFC'),
            sinalFR: getVal('prontuarioFR'),
            sinalTEMP: getVal('prontuarioTEMP'),
            sinalSATO2: getVal('prontuarioSATO2'),
            peso: getVal('prontuarioPeso'),
            altura: getVal('prontuarioAltura'),
            estadoGeral: getVal('prontuarioEstadoGeral'),
            cardioResp: getVal('prontuarioCardioResp'),
            neuroOutros: getVal('prontuarioNeuroOutros'),
            hipotese: getVal('prontuarioHipotese'),
            conduta: getVal('prontuarioConduta'),
            carimboAssinatura: carimboImg
        };

        const res = await fetch('/api/prontuarios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(novoProntuario)
        });

        if (res.ok) {
            alert("✅ Prontuário e registro de auditoria gravados com sucesso!");
            
            const form = document.getElementById('formNovoProntuario');
            if (form) form.reset();
            
            const preview = document.getElementById('prontuarioCarimboPreview');
            if (preview) preview.classList.add('d-none');

            await renderizarTabelaProntuarios();
            await atualizarPainelAtendimentos();
            await renderizarTabelaAuditoria(); 
            
            const tab = document.getElementById('tab-historico-prontuarios');
            if (tab && typeof bootstrap !== 'undefined') {
                bootstrap.Tab.getOrCreateInstance(tab).show();
            }
        } else {
            const errData = await res.json().catch(() => ({}));
            alert("❌ Erro ao salvar no banco de dados: " + (errData.error || `Código ${res.status}`));
        }
    } catch(e) {
        console.error("Erro na rotina de publicação do prontuário:", e);
        alert("❌ Ocorreu uma falha na requisição: " + e.message);
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = btnSubmit.dataset.texto;
        }
    }
}

async function renderizarTabelaProntuarios() {
    const tabela = document.getElementById('tabelaProntuarios');
    if (!tabela) return;

    try {
        const res = await fetch('/api/prontuarios');
        if (!res.ok) return;
        const prontuarios = await res.json();
        
        const inputBusca = document.getElementById('buscaPaciente');
        const termoBusca = inputBusca ? inputBusca.value.toLowerCase().trim() : '';

        tabela.innerHTML = '';

        const filtrados = prontuarios.filter(p => (p.nomePaciente || '').toLowerCase().includes(termoBusca) || (p.documento || '').toLowerCase().includes(termoBusca));

        if (filtrados.length === 0) {
            tabela.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-4">Nenhum prontuário localizado.</td></tr>`;
            return;
        }

        filtrados.forEach(p => {
            let cl = p.prioridade === 'Urgente' ? 'bg-warning text-dark' : (p.prioridade === 'Emergência' ? 'bg-danger text-white' : 'bg-success text-white');
            
            const carimboBruto = p.carimboAssinatura || p.assinatura || p.foto;
            const srcValida = obterUrlCarimboValida(carimboBruto);
            
            const avatarHtml = srcValida 
                ? `<img src="${srcValida}" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'rounded-circle bg-light d-flex align-items-center justify-content-center text-primary fw-bold border\\' style=\\'width: 50px; height: 50px;\\'><i class=\\'bi bi-person-badge fs-4\\'></i></div>';" class="rounded-circle object-fit-cover shadow-sm bg-white" style="width: 50px; height: 50px; border: 1px solid #dee2e6;">`
                : `<div class="rounded-circle bg-light d-flex align-items-center justify-content-center text-primary fw-bold border" style="width: 50px; height: 50px;"><i class="bi bi-person-badge fs-4"></i></div>`;

            tabela.insertAdjacentHTML('beforeend', `
                <tr>
                    <td>
                        <div class="d-flex align-items-center gap-3">
                            ${avatarHtml}
                            <div>
                                <h6 class="mb-1 fw-bold text-dark">${p.nomePaciente || 'Paciente Sem Nome'}</h6>
                                <div class="text-muted small">${p.tipoAtendimento || 'Consulta'} > ${p.convenioCartao || 'S/N'}</div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="badge bg-secondary mb-1">${p.especialidade || 'Geral'}</span><br>
                        <span class="badge ${cl}">${p.prioridade || 'Normal'}</span>
                    </td>
                    <td class="text-dark small">
                        <strong>Nasc:</strong> ${formatarDataBR(p.dataNascimento)}<br>
                        <span class="text-muted small">Gênero: ${p.genero || 'N/I'}</span><br>
                        <span class="text-primary fw-medium">Contato: ${p.contatoPaciente || 'N/I'}</span>
                    </td>
                    <td class="text-end text-nowrap">
                        <button class="btn btn-sm btn-outline-info" onclick="abrirProntuario(${p.id})">
                            <i class="bi bi-eye"></i> Ver
                        </button>
                    </td>
                </tr>
            `);
        });
    } catch(e) {
        console.error("Erro ao renderizar tabela de prontuários:", e);
    }
}

async function abrirProntuario(id) {
    try {
        const res = await fetch(`/api/prontuarios/${id}`);
        if (!res.ok) return alert("Prontuário não localizado.");
        
        const prontuario = await res.json();

        const setTxt = (elemId, val) => { if (document.getElementById(elemId)) document.getElementById(elemId).textContent = val || 'Não informado'; };
        const setVal = (elemId, val) => { if (document.getElementById(elemId)) document.getElementById(elemId).value = val || ''; };

        setTxt('editProntuarioNome', prontuario.nomePaciente);
        setTxt('editProntuarioNasc', formatarDataBR(prontuario.dataNascimento));
        setTxt('editProntuarioGenero', prontuario.genero);
        setTxt('editProntuarioCartao', prontuario.convenioCartao);
        setTxt('editProntuarioDocumento', prontuario.documento);
        setTxt('editProntuarioContato', prontuario.contatoPaciente);

        setVal('editProntuarioQP', prontuario.qp);
        setVal('editProntuarioHDA', prontuario.hda);
        setVal('editProntuarioHMP', prontuario.hmp);
        setVal('editProntuarioAlergias', prontuario.alergias);

        setVal('editProntuarioPA', prontuario.sinalPA);
        setVal('editProntuarioFC', prontuario.sinalFC);
        setVal('editProntuarioFR', prontuario.sinalFR);
        setVal('editProntuarioTEMP', prontuario.sinalTEMP);
        setVal('editProntuarioSATO2', prontuario.sinalSATO2);
        setVal('editProntuarioPeso', prontuario.peso);
        setVal('editProntuarioAltura', prontuario.altura);
        setVal('editProntuarioEstadoGeral', prontuario.estadoGeral);
        setVal('editProntuarioCardio', prontuario.cardioResp);
        setVal('editProntuarioNeuro', prontuario.neuroOutros);

        setVal('editProntuarioHD', prontuario.hipotese);
        setVal('editProntuarioConduta', prontuario.conduta);
        setVal('editProntuarioPrioridade', prontuario.prioridade || 'Normal');
        setTxt('editProntuarioRegistro', prontuario.registroProfissional || prontuario.crm_coren);

        const imgCarimbo = document.getElementById('editProntuarioCarimboView');
        const wrapper = document.getElementById('wrapperCarimboVisualizar');
        const carimboBruto = prontuario.carimboAssinatura || prontuario.assinatura || prontuario.foto;
        const srcValida = obterUrlCarimboValida(carimboBruto);

        if (imgCarimbo && wrapper) {
            if (srcValida) {
                imgCarimbo.src = srcValida;
                imgCarimbo.onerror = function() {
                    this.onerror = null;
                    wrapper.classList.add('d-none');
                };
                wrapper.classList.remove('d-none');
            } else {
                imgCarimbo.src = "";
                wrapper.classList.add('d-none');
            }
        }

        await renderizarTabelaAuditoria();

        const modalEl = document.getElementById('modalEditarProntuario');
        if (modalEl && typeof bootstrap !== 'undefined') {
            bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }
    } catch(e) {
        console.error("Erro ao abrir prontuário:", e);
    }
}

async function renderizarTabelaAuditoria() {
    const tabela = document.getElementById('tabelaAuditoria');
    if (!tabela) return;

    try {
        const res = await fetch('/api/prontuarios/auditoria');
        if (!res.ok) return;
        const logs = await res.json();
        
        tabela.innerHTML = '';

        if (logs.length === 0) {
            tabela.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">Nenhum log de acesso registrado ainda.</td></tr>`;
            return;
        }

        logs.forEach(l => {
            const badgeClass = l.acao === 'Criação' ? 'bg-success' : 'bg-info text-dark';
            tabela.insertAdjacentHTML('beforeend', `
                <tr>
                    <td class="fw-bold text-secondary">${l.data_hora}</td>
                    <td>
                        <strong>${l.nome_profissional || 'Desconhecido'}</strong><br>
                        <small class="text-muted">CRM/COREN: ${l.crm_coren || 'N/A'}</small>
                    </td>
                    <td><span class="badge ${badgeClass}">${l.acao}</span></td>
                    <td class="text-primary fw-bold">#${l.prontuario_id || 'N/A'}</td>
                    <td>${l.nome_paciente || 'Paciente Apagado/Inativo'}</td>
                </tr>
            `);
        });
    } catch(e) {
        console.error("Erro ao renderizar auditoria:", e);
    }
}

function formatarDataBR(dataString) {
    if (!dataString) return 'N/I';
    const partes = dataString.split('-');
    if (partes.length !== 3) return dataString;
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

function limparRastrosLocais() {
    localStorage.removeItem('loggedInUserCPF');
    localStorage.clear();
}

document.addEventListener('DOMContentLoaded', async () => {
    carregarDadosPerfil();
    
    const formNovoPaciente = document.getElementById('formNovoPaciente');
    if (formNovoPaciente) {
        formNovoPaciente.addEventListener('submit', cadastrarPaciente);
    }

    const formNovoProntuario = document.getElementById('formNovoProntuario');
    if (formNovoProntuario) {
        formNovoProntuario.addEventListener('submit', publicarProntuario);
    }

    const formNovaConsulta = document.getElementById('formNovaConsulta');
    if (formNovaConsulta) {
        formNovaConsulta.addEventListener('submit', agendarConsulta);
    }

    await atualizarDropdownPacientes();
    await atualizarDropdownProfissionais();
    
    await renderizarTabelaPacientes();
    await renderizarTabelaConsultas();
    await renderizarTabelaConsultasConcluidas();
    await renderizarTabelaProntuarios();
    await renderizarTabelaAuditoria();
    
    await renderizarMinhasConsultas();
    await renderizarMinhasConsultasConcluidas();
    await atualizarPainelAtendimentos();

    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, '0');
    const dia = String(hoje.getDate()).padStart(2, '0');
    const dataAtualFormatada = `${ano}-${mes}-${dia}`;

    const inputDataConsulta = document.getElementById('consultaData');
    if (inputDataConsulta) {
        inputDataConsulta.min = dataAtualFormatada;
    }

    const inputDataNasc = document.getElementById('pacienteDataNasc');
    if (inputDataNasc) {
        inputDataNasc.max = dataAtualFormatada;
    }

    const inputEditDataNasc = document.getElementById('editPacienteDataNasc');
    if (inputEditDataNasc) {
        inputEditDataNasc.max = dataAtualFormatada;
    }

    document.getElementById('buscaPaciente')?.addEventListener('input', renderizarTabelaProntuarios);
    document.getElementById('buscaPacienteLista')?.addEventListener('input', renderizarTabelaPacientes);
    document.getElementById('buscaConsulta')?.addEventListener('input', renderizarTabelaConsultas);
    document.getElementById('buscaConsultaConcluida')?.addEventListener('input', renderizarTabelaConsultasConcluidas);

    document.getElementById('tab-historico-prontuarios')?.addEventListener('shown.bs.tab', renderizarTabelaProntuarios);
    document.getElementById('tab-pacientes-cadastrados')?.addEventListener('shown.bs.tab', renderizarTabelaPacientes);
    document.getElementById('tab-consultas-agendadas')?.addEventListener('shown.bs.tab', renderizarTabelaConsultas);
    document.getElementById('tab-consultas-concluidas')?.addEventListener('shown.bs.tab', renderizarTabelaConsultasConcluidas);
    document.getElementById('tab-auditoria')?.addEventListener('shown.bs.tab', renderizarTabelaAuditoria);
    
    document.getElementById('tab-novo-prontuario')?.addEventListener('shown.bs.tab', atualizarDropdownPacientes);
    document.getElementById('tab-nova-consulta')?.addEventListener('shown.bs.tab', async () => {
        await atualizarDropdownPacientes();
        await atualizarDropdownProfissionais();
    });

    document.getElementById('tab-perfil-aba')?.addEventListener('shown.bs.tab', async () => {
        await atualizarPainelAtendimentos();
        await renderizarMinhasConsultas();
        await renderizarMinhasConsultasConcluidas();
    });
});