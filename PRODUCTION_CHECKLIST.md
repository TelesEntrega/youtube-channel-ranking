# Production Deployment Checklist

Sistema validado e pronto para produção. Use este checklist antes de escalar.

## 🔴 Prioridade ALTA (Crítico para Produção)

### ✅ Implementado

- [x] **Mostrar diff_percent no dashboard**
  - Tooltip em "Total Views" explicando origem
  - Card de auditoria em detalhes do canal
  - Indicadores visuais: ✅ <1%, ℹ️ 1-5%, ⚠️ >5%

- [x] **Mostrar última atualização do canal**
  - Coluna "Última Atualização" na tabela principal
  - Timestamp visível em detalhes

- [x] **Flag "dados auditados"**
  - Badge de qualidade baseado em diff_percent
  - Expander com detalhes de auditoria
  - Explicação de divergências esperadas

### 🎯 Pendente (CRÍTICO se público)

- [ ] **Log de execução por canal** ⚠️ MOVA AQUI SE FOR PÚBLICO
  - Criar tabela `channel_update_log` (run_id, channel_id, start_time, end_time, status, videos_updated, error_msg)
  - Essencial para responder: "Por que canal X não atualizou ontem?"
  - Sem isso, você fica cego em troubleshooting
  - **Motivo**: Em produção pública, logs por canal viram críticos, não opcionais

## 🟡 Prioridade MÉDIA (Recomendado antes de escalar)

- [ ] **Métricas de eficiência**
  - Dashboard mostra: "X vídeos atualizados de Y total" por canal
  - Estimativa de quota usada por run
  - Gráfico de quota usage ao longo do tempo
  - Tracking de quota/canal/dia como KPI

- [ ] **Alertas configuráveis** (granularidade refinada)
  - Email/Slack quando diff_percent > 10% (warning)
  - **Alerta CRÍTICO** quando diff_percent > 20% (provável erro de coleta)
  - Alerta quando quota > 80% do limite diário
  - Notificação de canais com erro consecutivo (2+ dias)
  - Rate de sucesso < 90%

- [ ] **Backup automático antes de cada run**
  - Script: `cp data/rankings.db data/backups/rankings_$(date +%Y%m%d_%H%M%S).db`
  - Retenção: últimos 7 dias
  - Verificar integridade com `sqlite3 backup.db "PRAGMA integrity_check"`
  - Testar restauração mensalmente

## 🟢 Prioridade BAIXA (Quando escalar >500 canais ou público)

- [ ] **Migração PostgreSQL**
  - ORDER BY RANDOM() → sampling determinístico
  - Indexes adicionais para queries complexas
  - Connection pooling

- [ ] **Backend separado (FastAPI)**
  - Endpoints REST: `/api/ranking`, `/api/channels/{id}`
  - Autenticação JWT se multi-user
  - Rate limiting por IP

- [ ] **Cache Redis (opcional)**
  - Cache de rankings frequentes (TTL: 1h)
  - Cache de channel details (TTL: 6h)
  - Reduz load no SQLite

- [ ] **Monitoramento**
  - Prometheus metrics
  - Grafana dashboards
  - Health check endpoint

## 📋 Validação Pré-Produção

### Dados de Teste
- [ ] Rodar com 3 canais conhecidos (pequeno, médio, grande)
- [ ] Comparar total_views com números do YouTube
- [ ] Verificar diff_percent < 5% na maioria dos casos

### Performance
- [ ] Testar com 50 canais
- [ ] Medir tempo de coleta (target: < 30min para 50 canais)
- [ ] Verificar quota usage (target: < 3000 units/run)

### Concorrência
- [ ] Testar atualização manual durante script agendado
- [ ] Verificar locks funcionando (nenhum "already being updated")

### Disaster Recovery
- [ ] **Backup automático configurado**
  - Script: `backup_db.sh` ou `backup_db.ps1`
  - Naming: `rankings_YYYYMMDD_HHMMSS.db`
  - Localização: `data/backups/`
  - Retenção: 7 dias (auto-cleanup de backups antigos)
- [ ] Testar restauração de backup (mensal)
- [ ] Documentar procedimento de rollback
- [ ] Validar integridade pós-backup (`PRAGMA integrity_check`)

## 🚀 Checklist de Deploy

### Ambiente
- [ ] Python 3.11+ instalado
- [ ] Dependências instaladas: `pip install -r requirements.txt`
- [ ] `.env` configurado com YT_API_KEY válida
- [ ] Pastas criadas: `data/`, `logs/`, `data/locks/`

### Testes
- [ ] `pytest tests/test_basic.py -v` passa (10/10)
- [ ] Dashboard abre: `streamlit run app/main.py`
- [ ] Adicionar primeiro canal via UI funciona

### Scheduling
- [ ] Task Scheduler (Windows) ou cron (Linux) configurado
- [ ] Script roda às 3AM diariamente
- [ ] Logs sendo salvos em `logs/collector.log`

### Monitoring
- [ ] Verificar logs diários
- [ ] Monitorar quota usage
- [ ] Alertas configurados (se aplicável)

## 📊 Métricas de Sucesso

### Reliability
- **Target**: 95%+ canais atualizados com sucesso diariamente
- **Medida**: `success_count / total_channels` em logs

### Accuracy
- **Target**: 90%+ canais com diff_percent < 5%
- **Medida**: Query no banco em `channel_snapshots`

### Performance
- **Target**: Coleta completa < 1 hora para 100 canais
- **Medida**: Tempo em logs de `run_daily_update.py`

### Quota Efficiency
- **Target**: < 50 units/canal/dia (modo incremental)
- **Medida**: Estimativa via logs ou dashboard

## 🔒 Security Checklist

- [x] API key em variável de ambiente (não hardcoded)
- [x] SQLite queries parametrizadas (injection-safe)
- [x] File permissions corretas em .env (read-only owner)
- [ ] **NUNCA expor Streamlit puro na internet** ⚠️
  - **Obrigatório**: Nginx reverse proxy OU Caddy OU Cloudflare Tunnel
  - HTTPS com certificado válido (Let's Encrypt)
  - Basic auth no mínimo (se público)
- [ ] Rate limiting se API pública (nginx limit_req)
- [ ] Firewall configurado (apenas portas necessárias)
- [ ] Logs de acesso habilitados

## 📚 Documentação

- [x] README.md completo
- [x] API key setup guide
- [x] Common issues troubleshooting
- [x] Architecture documentation
- [ ] Runbook para operação diária
- [ ] Incident response playbook

---

## 🎯 Next Steps por Escala

### Small (10-50 canais)
✅ Sistema atual está perfeito  
✅ Apenas implementar prioridade ALTA (já feito)

### Medium (50-200 canais)
🟡 Implementar prioridade MÉDIA  
🟡 Considerar PostgreSQL se muitos vídeos/canal

### Large (200-1000 canais)
🟢 Backend separado + cache  
🟢 Monitoramento robusto  
🟢 Equipe de operação

### Enterprise (1000+ canais ou SaaS público)
🔵 Arquitetura distribuída  
🔵 Multi-region  
🔵 24/7 support

---

**Versão Atual**: V1.0 Production-Ready  
**Última Revisão**: 2026-01-03  
**Aprovado para**: Low-Medium scale production
