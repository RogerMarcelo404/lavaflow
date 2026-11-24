DROP TABLE IF EXISTS caixa, pagamento, item_ordem, ordem_servico, assinatura,
    agendamento, preco_servico, servico, veiculo, cliente, usuario CASCADE;



CREATE TABLE usuario (
    id                  SERIAL PRIMARY KEY,
    nome                VARCHAR(100) NOT NULL,
    email               VARCHAR(150) NOT NULL UNIQUE,
    senha               VARCHAR(255) NOT NULL,
    perfil              VARCHAR(20)  NOT NULL,
    percentual_comissao NUMERIC(5,2),
    CONSTRAINT ck_usuario_perfil
        CHECK (perfil IN ('ADMIN', 'ATENDENTE', 'FUNCIONARIO')),
    CONSTRAINT ck_usuario_percentual
        CHECK (percentual_comissao IS NULL OR percentual_comissao BETWEEN 0 AND 100),
    CONSTRAINT ck_usuario_comissao_funcionario
        CHECK (perfil <> 'FUNCIONARIO' OR percentual_comissao IS NOT NULL)
);



CREATE TABLE cliente (
    id       SERIAL PRIMARY KEY,
    nome     VARCHAR(100) NOT NULL,
    telefone VARCHAR(20)  NOT NULL,
    cpf      VARCHAR(14)  UNIQUE
);



CREATE TABLE veiculo (
    id         SERIAL PRIMARY KEY,
    cliente_id INTEGER     NOT NULL REFERENCES cliente (id) ON DELETE CASCADE,
    placa      VARCHAR(8)  NOT NULL UNIQUE,
    modelo     VARCHAR(60) NOT NULL,
    porte      VARCHAR(10) NOT NULL,
    CONSTRAINT ck_veiculo_porte CHECK (porte IN ('PEQUENO', 'MEDIO', 'GRANDE'))
);



CREATE TABLE servico (
    id        SERIAL PRIMARY KEY,
    nome      VARCHAR(80)  NOT NULL UNIQUE,
    descricao VARCHAR(255)
);



CREATE TABLE preco_servico (
    id         SERIAL PRIMARY KEY,
    servico_id INTEGER       NOT NULL REFERENCES servico (id) ON DELETE CASCADE,
    porte      VARCHAR(10)   NOT NULL,
    valor      NUMERIC(10,2) NOT NULL,
    CONSTRAINT ck_preco_porte CHECK (porte IN ('PEQUENO', 'MEDIO', 'GRANDE')),
    CONSTRAINT ck_preco_valor CHECK (valor > 0),
    CONSTRAINT uq_preco_servico_porte UNIQUE (servico_id, porte)
);



CREATE TABLE agendamento (
    id         SERIAL PRIMARY KEY,
    veiculo_id INTEGER     NOT NULL REFERENCES veiculo (id) ON DELETE CASCADE,
    data       DATE        NOT NULL,
    turno      VARCHAR(10) NOT NULL,
    status     VARCHAR(15) NOT NULL DEFAULT 'AGENDADO',
    CONSTRAINT ck_agendamento_turno  CHECK (turno IN ('MANHA', 'TARDE')),
    CONSTRAINT ck_agendamento_status CHECK (status IN ('AGENDADO', 'ATENDIDO', 'CANCELADO'))
);



CREATE TABLE assinatura (
    id              SERIAL PRIMARY KEY,
    veiculo_id      INTEGER       NOT NULL REFERENCES veiculo (id) ON DELETE CASCADE,
    servico_id      INTEGER       NOT NULL REFERENCES servico (id),
    total_usos      INTEGER       NOT NULL,
    usos_restantes  INTEGER       NOT NULL,
    valor_mensal    NUMERIC(10,2) NOT NULL,
    data_vencimento DATE          NOT NULL,
    CONSTRAINT ck_assinatura_total CHECK (total_usos > 0),
    CONSTRAINT ck_assinatura_usos  CHECK (usos_restantes BETWEEN 0 AND total_usos),
    CONSTRAINT ck_assinatura_valor CHECK (valor_mensal > 0)
);



CREATE TABLE ordem_servico (
    id             SERIAL PRIMARY KEY,
    veiculo_id     INTEGER       NOT NULL REFERENCES veiculo (id),
    funcionario_id INTEGER       NOT NULL REFERENCES usuario (id),
    assinatura_id  INTEGER       REFERENCES assinatura (id),
    data           DATE          NOT NULL DEFAULT CURRENT_DATE,
    status         VARCHAR(15)   NOT NULL DEFAULT 'AGUARDANDO',
    valor_total    NUMERIC(10,2) NOT NULL DEFAULT 0,
    valor_comissao NUMERIC(10,2),
    CONSTRAINT ck_os_status
        CHECK (status IN ('AGUARDANDO', 'EM_ANDAMENTO', 'FINALIZADO', 'PAGO')),
    CONSTRAINT ck_os_valor CHECK (valor_total >= 0)
);



CREATE TABLE item_ordem (
    id         SERIAL PRIMARY KEY,
    ordem_id   INTEGER       NOT NULL REFERENCES ordem_servico (id) ON DELETE CASCADE,
    servico_id INTEGER       NOT NULL REFERENCES servico (id),
    preco      NUMERIC(10,2) NOT NULL,
    CONSTRAINT ck_item_preco CHECK (preco >= 0)
);



CREATE TABLE pagamento (
    id            SERIAL PRIMARY KEY,
    ordem_id      INTEGER       REFERENCES ordem_servico (id),
    assinatura_id INTEGER       REFERENCES assinatura (id),
    forma         VARCHAR(10)   NOT NULL,
    valor         NUMERIC(10,2) NOT NULL,
    data          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_pagamento_forma CHECK (forma IN ('DINHEIRO', 'PIX', 'CARTAO')),
    CONSTRAINT ck_pagamento_valor CHECK (valor > 0),
    CONSTRAINT ck_pagamento_origem
        CHECK ((ordem_id IS NOT NULL) <> (assinatura_id IS NOT NULL))
);



CREATE TABLE caixa (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER       NOT NULL REFERENCES usuario (id),
    data            DATE          NOT NULL UNIQUE,
    total_calculado NUMERIC(10,2) NOT NULL,
    valor_informado NUMERIC(10,2) NOT NULL
);



CREATE INDEX ix_os_data          ON ordem_servico (data);
CREATE INDEX ix_os_funcionario   ON ordem_servico (funcionario_id);
CREATE INDEX ix_agendamento_data ON agendamento (data, turno);
CREATE INDEX ix_pagamento_data   ON pagamento (data);
CREATE INDEX ix_veiculo_cliente  ON veiculo (cliente_id);