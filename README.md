# LavaFlow

Sistema web para gestão de lava-jatos e estéticas automotivas, desenvolvido no Projeto Integrador.

Organiza o atendimento do agendamento ao pagamento, com cálculo automático do preço pelo porte do veículo e da comissão dos funcionários, controle de pacotes mensais e fechamento de caixa.

**Integrantes:** Roger Marcelo, Rudjery Grando, Arthur Nicolli e Pedro Missel
**Professor:** Caio Vinicio Koch

## Tecnologias
- Python + Django
- HTML, CSS, JavaScript e Bootstrap 5
- PostgreSQL
- Postman (testes da API) e Figma (wireframes)

## Estrutura
- `database/` scripts do banco (DDL e DML)
- `lavaflow/` configurações do Django e conexão com o banco
- `core/` models, regras de negócio, API e telas
- `docs/` wireframes e coleção do Postman

## Como executar
1. No PostgreSQL, rodar os scripts da pasta `database` na ordem: `00_criar_banco.sql`, `01_ddl.sql` e `02_dml.sql`.
2. Copiar o `.env.example` para `.env` e colocar a senha do banco.
3. No terminal:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
4. Acessar http://127.0.0.1:8000 com `ana@lavaflow.com` e a senha `lavaflow123`.

## Wireframes
Arquivo no Figma: (https://www.figma.com/design/UCg2QT4abCG73g5xZuZdD9/Sem-t%C3%ADtulo?node-id=0-1&t=GdUxzc0iyNCFsI9r-1)

| Wireframe | Tela no sistema |

| [Login](docs/wireframes/01_login.png) 
| [Fila do dia](docs/wireframes/02_fila_do_dia.png) 
| [Fila no celular](docs/wireframes/03_fila_celular.png) 
| [Nova OS](docs/wireframes/04_nova_os.png) 
| [Clientes](docs/wireframes/05_clientes.png) 
| [Caixa](docs/wireframes/06_caixa.png) 

## API
A API recebe os dados em JSON, valida, salva ou consulta no banco e devolve a resposta. Os testes estão na coleção do Postman em `docs/api`.

| Método | Rota | Função |

| GET / POST | /api/clientes/ | Listar e cadastrar clientes |
| GET / POST | /api/veiculos/ | Buscar e cadastrar veículos |
| GET | /api/servicos/ | Serviços com preço por porte |
| GET / POST | /api/agendamentos/ | Agenda e novo agendamento |
| GET | /api/fila/ | Fila do dia |
| POST | /api/ordens/ | Abrir ordem de serviço |
| PATCH | /api/ordens/<id>/status/ | Avançar o status da OS |
| POST | /api/pagamentos/ | Registrar pagamento |
| GET / POST | /api/caixa/ | Resumo e fechamento do caixa |
| GET | /api/relatorios/comissoes/ | Comissões por funcionário |
