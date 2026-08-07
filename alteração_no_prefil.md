# Alteração de perfis no sistema

## Objetivo
Implementar suporte a três perfis de usuário no sistema:
- Admin
- Comum (Usuário)
- Atendente

## O que foi alterado

### Front-end
- O formulário de cadastro passou a exibir um seletor de perfil em vez da antiga opção binária de "Administrador?".
- A tela de usuários passou a mostrar o perfil de cada usuário em vez de apenas "Sim/Não".
- O modal de edição de usuários passou a editar o perfil por meio de um seletor.

### Back-end
- O fluxo de cadastro agora salva o perfil corretamente no banco de dados.
- O login e a sessão passaram a normalizar o valor do perfil para os três valores suportados.
- As regras de acesso foram ajustadas para reconhecer o perfil de administrador corretamente.

## Arquivos alterados
- templates/cadastro.html
- templates/usuarios.html
- templates/dashboard.html
- controllers/auth_controller.py
- models/usuario.py
- app.py
- static/usuarios.js
- tests/test_admin_and_security.py

## Comportamento esperado
- Usuários com perfil "Admin" têm acesso ao painel de usuários.
- Usuários com perfil "Comum" acessam o dashboard normalmente.
- Usuários com perfil "Atendente" também entram no sistema, com comportamento compatível com o fluxo atual.

## Validação
- Foi executado um teste de regressão para o cadastro com perfil "Comum".
- Resultado: 1 teste passou.
