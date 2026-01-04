# Daily Operations Runbook

Guia operacional passo a passo para manutenção diária do sistema de ranking de canais do YouTube.

---

## 📅 Rotina Diária (Automatizada)

### ✅ O que roda automaticamente

**Agendamento**: 3:00 AM (via Task Scheduler/cron)  
**Script**: `scripts/run_daily_update.py`  
**Duração esperada**: 20-40 minutos (50-100 canais)

#### Fluxo automático:
1. Script inicia coleta incremental
2. Para cada canal:
   - Busca vídeos novos (desde última atualização)
   - Atualiza views de vídeos recentes (90 dias)
   - Rotaciona 10% dos vídeos antigos
3. Salva snapshots diários
4. Registra logs em `logs/collector.log`

---

## 🔍 Check Matinal (10 minutos)

### 1. Verificar se rodou com sucesso

```powershell
# Ver últimas linhas do log
Get-Content logs\collector.log -Tail 50
```

**Buscar por:**
- ✅ `"Update complete"` - sucesso
- ✅ `"Successful: X/Y"` - contagem
- ❌ `"quotaExceeded"` - quota estourada
- ❌ `"ERROR"` - erros críticos

### 2. Conferir taxa de sucesso

**Target**: ≥95% canais atualizados

```sql
-- Rodar no SQLite
SELECT 
    COUNT(DISTINCT channel_id) as total_canais,
    COUNT(DISTINCT CASE WHEN snapshot_date = date('now') THEN channel_id END) as atualizados_hoje,
    ROUND(COUNT(DISTINCT CASE WHEN snapshot_date = date('now') THEN channel_id END) * 100.0 / COUNT(DISTINCT channel_id), 2) as taxa_sucesso
FROM channel_snapshots;
```

**Ação se < 95%:**
- Ver log para identificar canais falhados
- Verificar quota disponível
- Re-rodar manual se necessário

### 3. Verificar qualidade dos dados (diff_percent)

```sql
-- Canais com divergência alta (> 10%)
SELECT 
    c.title,
    cs.diff_percent,
    cs.total_views,
    cs.reported_channel_views,
    cs.snapshot_date
FROM channel_snapshots cs
JOIN channels c ON cs.channel_id = c.channel_id
WHERE cs.snapshot_date = date('now')
  AND cs.diff_percent > 10
ORDER BY cs.diff_percent DESC;
```

**Ação se diff_percent > 20%:**
- ⚠️ Possível erro de coleta
- Verificar logs do canal específico
- Re-coletar o canal manualmente

### 4. Quick health check

```bash
# Tempo desde última atualização
sqlite3 data/rankings.db "SELECT MAX(snapshot_date) FROM channel_snapshots;"

# Canais sem atualização recente (>2 dias)
sqlite3 data/rankings.db "SELECT c.title, MAX(cs.snapshot_date) as last_update FROM channels c JOIN channel_snapshots cs ON c.channel_id = cs.channel_id GROUP BY c.channel_id HAVING last_update < date('now', '-2 days');"
```

---

## 🚨 Troubleshooting Comum

### Problema 1: Quota Excedida

**Sintoma**: Log mostra `quotaExceeded`

**Diagnóstico:**
```bash
# Contar requests do dia (aproximado via logs)
grep "Fetching details" logs/collector.log | wc -l
```

**Solução imediata:**
- ⏸️ Pausar coletas até reset (meia-noite Pacific Time)
- ✅ Continua amanhã automaticamente

**Prevenção:**
- Reduzir número de canais
- Aumentar intervalo de rotação (10% → 5%)
- Modo incremental sempre ativo

### Problema 2: Canal não atualiza

**Sintoma**: Canal específico sem snapshot recente

**Diagnóstico:**
```bash
# Buscar erros do canal no log
grep "CHANNEL_ID" logs/collector.log | tail -20
```

**Causas comuns:**
- Canal deletado/suspenso
- API temporariamente indisponível
- Vídeos todos privados

**Solução:**
```bash
# Re-coletar manualmente
python -c "from app.collector import Collector; from app.db import Database; from app.youtube_client import YouTubeClient; import os; db = Database(); yt = YouTubeClient(os.getenv('YT_API_KEY')); c = Collector(yt, db); print(c.collect_channel('CHANNEL_ID', mode='full'))"
```

### Problema 3: Database locked

**Sintoma**: `database is locked` no log

**Causa**: Dois processos acessando simultaneamente

**Solução:**
```bash
# Verificar processos Python rodando
Get-Process python

# Matar processo travado (se necessário)
Stop-Process -Id PID

# Aguardar locks expirarem (file locks auto-release)
```

### Problema 4: Divergência alta (>20%)

**Sintoma**: diff_percent consistentemente alto

**Diagnóstico:**
```sql
-- Ver evolução da divergência
SELECT snapshot_date, diff_percent, total_views, reported_channel_views
FROM channel_snapshots
WHERE channel_id = 'CHANNEL_ID'
ORDER BY snapshot_date DESC
LIMIT 10;
```

**Causas prováveis:**
- Muitos vídeos privados/removidos recentemente
- Erro na paginação (vídeos faltando)
- Canal com conteúdo não-indexável

**Ação:**
- Re-coletar em modo `full` (não incremental)
- Verificar se `videoCount` do canal bate com total coletado
- Se persistir: marcar canal para investigação manual

---

## 🔧 Tarefas Semanais (30 minutos)

### Segunda-feira: Review de quota

```bash
# Estimar quota usage semanal
grep -E "quota|Fetching details" logs/collector.log | grep "$(date -d '7 days ago' +%Y-%m-%d)" -A 1000 | wc -l
```

**Target**: <3000 units/dia (modo incremental)

### Quarta-feira: Backup validation

```bash
# Listar backups
ls -lh data/backups/

# Testar restauração do backup mais recente
cp data/backups/rankings_*.db /tmp/test_restore.db
sqlite3 /tmp/test_restore.db "PRAGMA integrity_check;"
```

### Sexta-feira: Performance review

```sql
-- Canais mais lentos (mais vídeos)
SELECT c.title, COUNT(v.video_id) as total_videos
FROM channels c
JOIN videos v ON c.channel_id = v.channel_id
GROUP BY c.channel_id
ORDER BY total_videos DESC
LIMIT 10;

-- Snapshots criados na semana
SELECT snapshot_date, COUNT(*) as canais_atualizados
FROM channel_snapshots
WHERE snapshot_date >= date('now', '-7 days')
GROUP BY snapshot_date
ORDER BY snapshot_date DESC;
```

---

## 📊 Métricas KPI (Mensal)

### Reliability
```sql
-- Taxa de sucesso mensal
SELECT 
    strftime('%Y-%m', snapshot_date) as mes,
    COUNT(DISTINCT channel_id) * 1.0 / 
        (SELECT COUNT(*) FROM channels) * 100 as taxa_cobertura_media
FROM channel_snapshots
WHERE snapshot_date >= date('now', '-30 days')
GROUP BY mes;
```

**Target**: ≥95%

### Accuracy
```sql
-- Distribuição de divergências
SELECT 
    CASE 
        WHEN diff_percent < 1 THEN '< 1% (excelente)'
        WHEN diff_percent < 5 THEN '1-5% (bom)'
        WHEN diff_percent < 10 THEN '5-10% (aceitável)'
        ELSE '> 10% (atenção)'
    END as faixa,
    COUNT(*) as canais
FROM channel_snapshots
WHERE snapshot_date >= date('now', '-30 days')
  AND diff_percent IS NOT NULL
GROUP BY faixa;
```

**Target**: 90%+ em "excelente" ou "bom"

### Performance
```bash
# Tempo médio de execução (parsing de logs)
grep "Update complete" logs/collector.log | awk '{print $1, $2}' | uniq -c
```

**Target**: <1 hora para 100 canais

### Quota Efficiency
```bash
# Units/canal/dia (estimativa via logs)
# Fórmula aproximada: (requests * 1 unit) / canais
```

**Target**: <50 units/canal/dia (incremental)

---

## 🆘 Disaster Recovery

### Cenário 1: Database corrompido

```bash
# 1. Parar todas operações
# 2. Restaurar último backup
cp data/backups/rankings_YYYYMMDD_HHMMSS.db data/rankings.db

# 3. Verificar integridade
sqlite3 data/rankings.db "PRAGMA integrity_check;"

# 4. Re-rodar coleta do dia
python scripts/run_daily_update.py
```

### Cenário 2: Quota excedida antes do fim do dia

```bash
# 1. Identificar consumo excessivo
grep "quotaExceeded" logs/collector.log

# 2. Pausar coletas até reset (00:00 Pacific Time)
# 3. Documentar causa raiz
# 4. Ajustar estratégia:
#    - Reduzir rotação de vídeos antigos
#    - Aumentar intervalo entre updates
#    - Priorizar canais críticos
```

### Cenário 3: Perda de dados (sem backup)

**Prevenção é crítica - não há recuperação perfeita**

Opções limitadas:
1. Re-coletar todos os canais (modo full)
2. Perda de histórico de snapshots (não recuperável)

---

## 📞 Escalation Matrix

### Problema de Rotina (self-service)
- Canal individual falhando → re-coletar manual
- Divergência pontual → investigar logs
- Performance lenta → revisar query/índices

### Problema Operacional (requer atenção)
- Taxa de sucesso < 90% por 2+ dias
- Quota consistentemente alta
- Backups falhando

### Incidente Crítico (urgente)
- Database corrompido
- Quota zerada antes do dia acabar
- Sistema totalmente parado

---

## 🎯 Checklist Diário (Quick Reference)

### Manhã (5 min)
- [ ] Ver log: última execução bem-sucedida?
- [ ] Taxa de sucesso ≥ 95%?
- [ ] Divergências < 10% na maioria?

### Semanal (30 min)
- [ ] Review de quota usage
- [ ] Testar backup restoration
- [ ] Performance metrics

### Mensal (1h)
- [ ] KPIs documentados
- [ ] Cleanup de logs antigos (>30 dias)
- [ ] Cleanup de backups (>7 dias)
- [ ] Review de canais inativos

---

## 📝 Logging Best Practices

### O que sempre verificar nos logs:

**✅ Indicadores de sucesso:**
```
"Update complete"
"Successful: X/Y"
"Created snapshot"
"Saved N videos"
```

**⚠️ Warnings normais (aceitáveis):**
```
"Video ID sem estatísticas"  # vídeo privado/deletado
"Divergência X%"              # se < 10%
"Paginação incompleta"        # canal muito grande
```

**❌ Erros críticos (agir):**
```
"quotaExceeded"              # parar coletas
"403 Forbidden"              # API key inválida
"database is locked"         # concorrência
"KeyError"                   # bug no código
```

---

**Versão**: 1.0  
**Última atualização**: 2026-01-03  
**Responsável**: Equipe de Operações

---

## 🔗 Links Úteis

- [YouTube API Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost)
- [SQLite CLI Reference](https://sqlite.org/cli.html)
- [Streamlit Docs](https://docs.streamlit.io)
- Production Checklist: `PRODUCTION_CHECKLIST.md`
- Architecture Docs: `implementation_plan.md`
