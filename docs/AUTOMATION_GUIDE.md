# 🤖 Automação de Snapshots - Guia de Configuração

Este guia explica como configurar a coleta automática de snapshots (sem intervenção manual).

---

## ⏰ Script de Automação

O script [`scripts/collect_snapshots.py`](../scripts/collect_snapshots.py) já está pronto para uso automatizado.

---

## 🪟 Windows - Task Scheduler

### Criar Tarefa Agendada

1. Abra o **Task Scheduler** (Agendador de Tarefas)
2. Clique em **Create Basic Task** (Criar Tarefa Básica)
3. Configure:

**Nome:** `YouTube Ranking - Snapshot Diário`  
**Descrição:** `Coleta automática de snapshots de vídeos e canais`

**Trigger (Gatilho):**
- **Daily** (Diário)
- **Start:** 02:00:00
- **Recur every:** 1 day

**Action (Ação):**
- **Start a Program** (Iniciar um programa)
- **Program/script:**
  ```
  C:\Users\Rankine\Documents\Ranking Gorgonoid\venv\Scripts\python.exe
  ```
- **Add arguments:**
  ```
  scripts\collect_snapshots.py
  ```
- **Start in:**
  ```
  C:\Users\Rankine\Documents\Ranking Gorgonoid
  ```

**Settings (Configurações):**
- ✅ Run whether user is logged on or not
- ✅ Run with highest privileges
- ✅ If the task fails, restart every: 10 minutes (3 attempts)

---

## 🐧 Linux - Crontab

```bash
# Editar crontab
crontab -e

# Adicionar linha (02:00 diariamente)
0 2 * * * cd /path/to/Ranking\ Gorgonoid && /path/to/venv/bin/python scripts/collect_snapshots.py >> logs/cron.log 2>&1
```

---

## 🐳 Docker - Cron Container

Adicione ao `Dockerfile`:

```dockerfile
# Install cron
RUN apt-get update && apt-get install -y cron

# Copy cron job
COPY crontab /etc/cron.d/snapshot-cron
RUN chmod 0644 /etc/cron.d/snapshot-cron
RUN crontab /etc/cron.d/snapshot-cron

# Start cron in entrypoint
CMD cron && streamlit run app/main.py
```

Arquivo `crontab`:
```
0 2 * * * cd /app && python scripts/collect_snapshots.py >> /app/logs/cron.log 2>&1
```

---

## 📊 Monitoramento

### Verificar última execução

```powershell
# Windows
Get-Content logs\collector.log -Tail 50

# Linux
tail -n 50 logs/collector.log
```

### Validar snapshots no banco

```powershell
# Windows
python -c "from app.db import Database; db = Database('data/rankings.db'); print(db.get_snapshot_stats())"
```

Esperado:
```json
{
  "total_snapshots": 12000,
  "videos_tracked": 150,
  "unique_dates": 30,
  "latest_date": "2026-01-04"
}
```

---

## ⚠️ Troubleshooting

### Erro: "API quota exceeded"
- **Causa:** Muitas chamadas no mesmo dia
- **Solução:** Reduza a frequência ou use pool de API keys

### Erro: "No channels found"
- **Causa:** Banco vazio
- **Solução:** Adicione canais via interface antes de automatizar

### Snapshot não aparece
- **Causa:** Script não rodou ou falhou
- **Solução:** Verifique logs em `logs/collector.log`

---

## 🔐 Segurança

**Nunca** versione`:
- `.env` (contém `YT_API_KEY`)
- `data/*.db` (dados privados)
- `logs/*.log` (podem conter IDs sensíveis)

Use `.gitignore` correto (já configurado).

---

**Última atualização:** 2026-01-04
