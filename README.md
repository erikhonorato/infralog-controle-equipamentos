# InfraLog - Sistema funcional

Versão em Flask e SQLite baseada na prototipação do projeto.

## Antes de executar

Copie sua logo para `static/img/logo.png`. Caso a imagem não exista, o cabeçalho mostrará o texto InfraLog.

## Executar no Windows

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py criar_banco.py
py app.py
```

Acesse `http://127.0.0.1:5000`.

## Funcionalidades

- Cadastro e consulta de equipamentos
- Cadastro e consulta de colaboradores
- Registro de empréstimos
- Bloqueio de equipamento indisponível
- Registro de devolução
- Atualização automática da situação do equipamento
