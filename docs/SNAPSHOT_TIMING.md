# 📅 Padronização Temporal - Sistema de Snapshots

## Horário de Referência Oficial

**Horário padrão:** 02:00 BRT (Brasília Time)

### Motivo da Escolha
- Menor tráfego na API do YouTube
- Horário consistente entre dias úteis e fins de semana
- Após meia-noite (representa "fechamento do dia anterior")

---

## Regras de Snapshot

### Snapshot Diário
- **O que:** View count de todos os vídeos + channel statistics
- **Quando:** Diariamente às 02:00 BRT
- **Formato da data:** `YYYY-MM-DD` (ex: `2026-01-04`)
- **Sincronização:** Vídeos e canal DEVEM ter a mesma `snapshot_date`

### Seleção de Snapshots para Análise

Ao calcular ranking de um período `[start_date, end_date]`:

**Snapshot Início:**
```sql
SELECT snapshot_date FROM video_snapshots 
WHERE snapshot_date >= start_date
ORDER BY snapshot_date ASC
LIMIT 1
```
(Primeiro snapshot disponível em ou após a data de início)

**Snapshot Fim:**
```sql
SELECT snapshot_date FROM video_snapshots 
WHERE snapshot_date <= end_date
ORDER BY snapshot_date DESC
LIMIT 1
```
(Último snapshot disponível em ou antes da data de fim)

---

## Consistência de Dados

### Validação
Antes de calcular Delta Canal ou Delta Conteúdo, verificar:
1. ✅ Snapshot de canal existe para a data?
2. ✅ Snapshot de vídeos existe para a data?
3. ✅ Ambos têm a mesma `snapshot_date`?

### Tratamento de Falhas
- Se snapshot parcial (vídeos sem canal ou vice-versa): **bloquear cálculo**
- Se snapshot ausente para período: exibir erro claro ao usuário
- Nunca interpolar ou estimar valores ausentes

---

## Automação

Ver [`scripts/collect_snapshots.py`](../scripts/collect_snapshots.py) para coletor automático.

**Agendamento recomendado:**
- Windows: Task Scheduler
- Linux: Crontab (`0 2 * * *`)
- Docker: Cron container ou entrypoint script

---

## Auditoria

Para verificar cobertura de snapshots:

```sql
-- Coverage por data
SELECT 
    snapshot_date,
    COUNT(DISTINCT video_id) as videos,
    COUNT(DISTINCT channel_id) as channels
FROM video_snapshots
GROUP BY snapshot_date
ORDER BY snapshot_date DESC;

-- Canais sem snapshot recente
SELECT c.channel_id, c.title, MAX(cs.snapshot_date) as last_snapshot
FROM channels c
LEFT JOIN channel_snapshots cs ON c.channel_id = cs.channel_id
GROUP BY c.channel_id
HAVING last_snapshot < DATE('now', '-1 day') OR last_snapshot IS NULL;
```

---

**Última atualização:** 2026-01-04
