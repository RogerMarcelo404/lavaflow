BEGIN;

INSERT INTO usuario (nome, email, senha, perfil, percentual_comissao) VALUES
('Carlos Andrade', 'admin@lavaflow.com',
 'pbkdf2_sha256$600000$lavaflowseed2026$DQ2wTgCPnlueKYfuUTvmsUt/5uK59WVU5/5zN732kIc=', 'ADMIN', NULL),
('Ana Paula Rocha', 'ana@lavaflow.com',
 'pbkdf2_sha256$600000$lavaflowseed2026$DQ2wTgCPnlueKYfuUTvmsUt/5uK59WVU5/5zN732kIc=', 'ATENDENTE', NULL),
('Pedro Henrique Alves', 'pedro@lavaflow.com',
 'pbkdf2_sha256$600000$lavaflowseed2026$DQ2wTgCPnlueKYfuUTvmsUt/5uK59WVU5/5zN732kIc=', 'FUNCIONARIO', 30.00),
('Lucas Ferreira', 'lucas@lavaflow.com',
 'pbkdf2_sha256$600000$lavaflowseed2026$DQ2wTgCPnlueKYfuUTvmsUt/5uK59WVU5/5zN732kIc=', 'FUNCIONARIO', 25.00);



INSERT INTO servico (nome, descricao) VALUES
('Lavagem simples',      'Lavagem externa com shampoo neutro e secagem'),
('Lavagem completa',     'Lavagem externa, aspiração interna e limpeza de painel'),
('Cera',                 'Aplicação de cera protetora na pintura'),
('Higienização interna', 'Limpeza profunda de bancos, carpetes e teto'),
('Polimento',            'Polimento técnico da pintura para remover riscos leves');



INSERT INTO preco_servico (servico_id, porte, valor)
SELECT s.id, p.porte, p.valor
FROM servico s
JOIN (VALUES
    ('Lavagem simples',      'PEQUENO',  35.00), ('Lavagem simples',      'MEDIO',  45.00), ('Lavagem simples',      'GRANDE',  60.00),
    ('Lavagem completa',     'PEQUENO',  50.00), ('Lavagem completa',     'MEDIO',  65.00), ('Lavagem completa',     'GRANDE',  85.00),
    ('Cera',                 'PEQUENO',  30.00), ('Cera',                 'MEDIO',  40.00), ('Cera',                 'GRANDE',  50.00),
    ('Higienização interna', 'PEQUENO', 150.00), ('Higienização interna', 'MEDIO', 180.00), ('Higienização interna', 'GRANDE', 230.00),
    ('Polimento',            'PEQUENO', 180.00), ('Polimento',            'MEDIO', 220.00), ('Polimento',            'GRANDE', 280.00)
) AS p (servico, porte, valor) ON p.servico = s.nome;



INSERT INTO cliente (nome, telefone, cpf) VALUES
('João Silva',     '(11) 98888-1001', '123.456.789-09'),
('Maria Souza',    '(11) 98888-1002', '234.567.890-92'),
('Roberto Lima',   '(11) 98888-1003', '345.678.901-75'),
('Fernanda Costa', '(11) 98888-1004', '456.789.012-49'),
('Paulo Mendes',   '(11) 98888-1005', NULL);



INSERT INTO veiculo (cliente_id, placa, modelo, porte) VALUES
((SELECT id FROM cliente WHERE nome = 'João Silva'),     'ABC1D23', 'Chevrolet Onix',  'MEDIO'),
((SELECT id FROM cliente WHERE nome = 'Maria Souza'),    'QWE2R34', 'Hyundai HB20',    'PEQUENO'),
((SELECT id FROM cliente WHERE nome = 'Roberto Lima'),   'RTY3U45', 'Toyota Hilux',    'GRANDE'),
((SELECT id FROM cliente WHERE nome = 'Fernanda Costa'), 'ZXC4V56', 'Jeep Compass',    'GRANDE'),
((SELECT id FROM cliente WHERE nome = 'Fernanda Costa'), 'BNM5K67', 'Renault Kwid',    'PEQUENO'),
((SELECT id FROM cliente WHERE nome = 'Paulo Mendes'),   'JKL6M78', 'Toyota Corolla',  'MEDIO');



INSERT INTO assinatura (veiculo_id, servico_id, total_usos, usos_restantes, valor_mensal, data_vencimento) VALUES
((SELECT id FROM veiculo WHERE placa = 'ABC1D23'), (SELECT id FROM servico WHERE nome = 'Lavagem simples'),
 4, 2, 160.00, CURRENT_DATE + 20),
((SELECT id FROM veiculo WHERE placa = 'QWE2R34'), (SELECT id FROM servico WHERE nome = 'Lavagem simples'),
 4, 1, 120.00, CURRENT_DATE - 5);



INSERT INTO agendamento (veiculo_id, data, turno, status) VALUES
((SELECT id FROM veiculo WHERE placa = 'ABC1D23'), CURRENT_DATE,     'MANHA', 'ATENDIDO'),
((SELECT id FROM veiculo WHERE placa = 'BNM5K67'), CURRENT_DATE,     'MANHA', 'ATENDIDO'),
((SELECT id FROM veiculo WHERE placa = 'JKL6M78'), CURRENT_DATE,     'TARDE', 'CANCELADO'),
((SELECT id FROM veiculo WHERE placa = 'RTY3U45'), CURRENT_DATE + 1, 'MANHA', 'AGENDADO'),
((SELECT id FROM veiculo WHERE placa = 'JKL6M78'), CURRENT_DATE + 1, 'TARDE', 'AGENDADO');



INSERT INTO ordem_servico (veiculo_id, funcionario_id, assinatura_id, data, status, valor_total, valor_comissao) VALUES
((SELECT id FROM veiculo WHERE placa = 'RTY3U45'), (SELECT id FROM usuario WHERE email = 'pedro@lavaflow.com'),
 NULL, CURRENT_DATE - 1, 'PAGO', 135.00, 40.50),
((SELECT id FROM veiculo WHERE placa = 'JKL6M78'), (SELECT id FROM usuario WHERE email = 'lucas@lavaflow.com'),
 NULL, CURRENT_DATE - 1, 'PAGO', 220.00, 55.00),
((SELECT id FROM veiculo WHERE placa = 'ABC1D23'), (SELECT id FROM usuario WHERE email = 'pedro@lavaflow.com'),
 (SELECT a.id FROM assinatura a JOIN veiculo v ON v.id = a.veiculo_id WHERE v.placa = 'ABC1D23'),
 CURRENT_DATE - 1, 'PAGO', 0.00, 12.00);



INSERT INTO ordem_servico (veiculo_id, funcionario_id, assinatura_id, data, status, valor_total) VALUES
((SELECT id FROM veiculo WHERE placa = 'ABC1D23'), (SELECT id FROM usuario WHERE email = 'pedro@lavaflow.com'),
 (SELECT a.id FROM assinatura a JOIN veiculo v ON v.id = a.veiculo_id WHERE v.placa = 'ABC1D23'),
 CURRENT_DATE, 'AGUARDANDO', 0.00),
((SELECT id FROM veiculo WHERE placa = 'BNM5K67'), (SELECT id FROM usuario WHERE email = 'pedro@lavaflow.com'),
 NULL, CURRENT_DATE, 'AGUARDANDO', 50.00),
((SELECT id FROM veiculo WHERE placa = 'ZXC4V56'), (SELECT id FROM usuario WHERE email = 'lucas@lavaflow.com'),
 NULL, CURRENT_DATE, 'EM_ANDAMENTO', 230.00),
((SELECT id FROM veiculo WHERE placa = 'QWE2R34'), (SELECT id FROM usuario WHERE email = 'pedro@lavaflow.com'),
 NULL, CURRENT_DATE, 'FINALIZADO', 35.00);



INSERT INTO item_ordem (ordem_id, servico_id, preco)
SELECT os.id, s.id, i.preco
FROM (VALUES
    ('RTY3U45', -1, 'Lavagem completa',      85.00),
    ('RTY3U45', -1, 'Cera',                  50.00),
    ('JKL6M78', -1, 'Polimento',            220.00),
    ('ABC1D23', -1, 'Lavagem simples',        0.00),
    ('ABC1D23',  0, 'Lavagem simples',        0.00),
    ('BNM5K67',  0, 'Lavagem completa',      50.00),
    ('ZXC4V56',  0, 'Higienização interna', 230.00),
    ('QWE2R34',  0, 'Lavagem simples',       35.00)
) AS i (placa, dias, servico, preco)
JOIN veiculo v       ON v.placa = i.placa
JOIN ordem_servico os ON os.veiculo_id = v.id AND os.data = CURRENT_DATE + i.dias
JOIN servico s       ON s.nome = i.servico;



INSERT INTO pagamento (ordem_id, assinatura_id, forma, valor, data) VALUES
(NULL, (SELECT a.id FROM assinatura a JOIN veiculo v ON v.id = a.veiculo_id WHERE v.placa = 'ABC1D23'),
 'PIX', 160.00, NOW() - INTERVAL '10 days');



INSERT INTO pagamento (ordem_id, forma, valor, data)
SELECT os.id, p.forma, p.valor, NOW() - INTERVAL '1 day'
FROM (VALUES ('RTY3U45', 'PIX', 135.00), ('JKL6M78', 'CARTAO', 220.00)) AS p (placa, forma, valor)
JOIN veiculo v        ON v.placa = p.placa
JOIN ordem_servico os ON os.veiculo_id = v.id AND os.data = CURRENT_DATE - 1;



INSERT INTO caixa (usuario_id, data, total_calculado, valor_informado) VALUES
((SELECT id FROM usuario WHERE email = 'ana@lavaflow.com'), CURRENT_DATE - 1, 355.00, 350.00);

COMMIT;