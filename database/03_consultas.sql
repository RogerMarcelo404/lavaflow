SELECT os.id, v.placa, v.modelo, c.nome AS cliente, u.nome AS funcionario,
       os.status, os.valor_total
FROM ordem_servico os
JOIN veiculo v ON v.id = os.veiculo_id
JOIN cliente c ON c.id = v.cliente_id
JOIN usuario u ON u.id = os.funcionario_id
WHERE os.data = CURRENT_DATE
ORDER BY CASE os.status WHEN 'EM_ANDAMENTO' THEN 1 WHEN 'AGUARDANDO' THEN 2
                        WHEN 'FINALIZADO' THEN 3 ELSE 4 END, os.id;




SELECT s.nome AS servico, v.placa, v.porte, p.valor
FROM veiculo v
JOIN preco_servico p ON p.porte = v.porte
JOIN servico s ON s.id = p.servico_id
WHERE v.placa = 'ABC1D23' AND s.nome = 'Lavagem completa';



SELECT turno, COUNT(*) AS ocupadas
FROM agendamento
WHERE data = CURRENT_DATE + 1 AND status <> 'CANCELADO'
GROUP BY turno;



SELECT a.id, s.nome AS servico, a.usos_restantes, a.data_vencimento
FROM assinatura a
JOIN veiculo v ON v.id = a.veiculo_id
JOIN servico s ON s.id = a.servico_id
WHERE v.placa = 'ABC1D23'
  AND a.data_vencimento >= CURRENT_DATE
  AND a.usos_restantes > 0;



SELECT forma, COUNT(*) AS quantidade, SUM(valor) AS total
FROM pagamento
WHERE data >= CURRENT_DATE - 30
GROUP BY forma
ORDER BY total DESC;



SELECT s.nome, COUNT(*) AS vezes
FROM item_ordem i
JOIN servico s ON s.id = i.servico_id
GROUP BY s.nome
ORDER BY vezes DESC;



SELECT u.nome, COUNT(os.id) AS ordens, SUM(os.valor_comissao) AS comissao
FROM ordem_servico os
JOIN usuario u ON u.id = os.funcionario_id
WHERE os.status = 'PAGO'
  AND os.data >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY u.nome
ORDER BY comissao DESC;



SELECT data, total_calculado, valor_informado,
       valor_informado - total_calculado AS diferenca
FROM caixa
ORDER BY data DESC;



BEGIN;
UPDATE ordem_servico SET status = 'EM_ANDAMENTO'
WHERE id = (SELECT MIN(id) FROM ordem_servico
            WHERE data = CURRENT_DATE AND status = 'AGUARDANDO');
SELECT id, status FROM ordem_servico WHERE data = CURRENT_DATE ORDER BY id;
ROLLBACK;



DELETE FROM agendamento
WHERE status = 'CANCELADO' AND data < CURRENT_DATE - 90;
