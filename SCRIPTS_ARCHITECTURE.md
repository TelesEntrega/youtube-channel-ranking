# Arquitetura do Sistema e Documentação dos Scripts

Este documento detalha todos os componentes do sistema de Ranking do YouTube, explicando a função de cada script, suas dependências e como os dados fluem. Use este guia para auditar a lógica e identificar possíveis pontos de falha.

## 📁 Estrutura de Diretórios

```plaintext
Rankine Gorgonoid/
├── app/                  # Núcleo da aplicação (Lógica Backend)
│   ├── main.py           # Dashboard (Frontend Streamlit)
│   ├── db.py             # Gerenciamento de Banco de Dados
│   ├── youtube_client.py # Comunicação com API do YouTube
│   ├── collector.py      # Motor de Coleta de Dados
│   ├── ranking.py        # Motor de Cálculo de Ranking
│   └── utils.py          # Utilitários (File Lock, Config)
│
├── scripts/              # Automação e Ferramentas
│   ├── run_daily_update.py      # Script de Execução Diária
│   ├── validate_against_video.py # Validação de Qualidade
│   └── simulate_history.py      # (Temp) Gerador de Dados Simulados
│
└── iniciar_sistema.bat   # Launcher "One-Click"
```

---

## 🧠 Núcleo da Aplicação (`app/`)

### 1. `app/youtube_client.py` (A Janela para o Mundo)
**Função:** Interage diretamente com a API do YouTube.
- **Responsabilidades:**
  - Resolver Handles (`@google` -> `Channel ID`).
  - Buscar vídeos de um canal (Paginação automática).
  - Obter detalhes de vídeos (Duração, Views, Datas).
  - **Lógica Crítica:** Detecta se é Short ou Longo baseado na duração (`<= 60s`).
  - **Tratamento de Erros:** Implementa retries exponenciais e fallback para `search().list` se o handle falhar.

### 2. `app/collector.py` (O Operário)
**Função:** Orquestra a atualização dos dados.
- **Responsabilidades:**
  - Decide o que coletar: `full` (tudo) ou `incremental` (novos vídeos + rotação de antigos).
  - Chama o `youtube_client` para pegar dados brutos.
  - Chama o `db` para salvar.
  - Gera logs de execução.

### 3. `app/db.py` (A Memória)
**Função:** Gerencia o banco de dados SQLite (`data/rankings.db`).
- **Responsabilidades:**
  - Cria tabelas (`channels`, `videos`, `channel_snapshots`).
  - **Cálculo de Snapshot:** Agrega as views de todos os vídeos de um canal em um dado dia e salva em `channel_snapshots`.
  - **Exclusão em Cascata:** Se deletar um canal, remove vídeos e snapshots automaticamente (`ON DELETE CASCADE`).

### 4. `app/ranking.py` (O Analista)
**Função:** Processa dados para exibição.
- **Responsabilidades:**
  - Calcula o ranking global somando views.
  - Gera dados para o gráfico comparativo (`get_comparison_data`), filtrando por data.

### 5. `app/main.py` (A Interface)
**Função:** Interface visual feita em Streamlit.
- **Responsabilidades:**
  - Exibe tabelas, métricas e gráficos.
  - **Lógica de Comparação:** Normaliza os dados do gráfico (subtrai o valor inicial) para mostrar apenas o "Crescimento no Período".

---

## 🤖 Scripts de Automação (`scripts/`)

### 1. `scripts/run_daily_update.py`
**Comando:** `python scripts/run_daily_update.py`
**Função:** Script mestre para rodar no Agendador de Tarefas (Cron).
- **Fluxo:**
  1. Carrega variáveis de ambiente (`.env`).
  2. Conecta no banco.
  3. Itera sobre todos os canais cadastrados.
  4. Executa `collector.collect_channel(mode='incremental')`.
  5. Cria um `snapshot` diário com os totais atualizados.

### 2. `scripts/validate_against_video.py`
**Comando:** `python scripts/validate_against_video.py @canal`
**Função:** Auditoria de qualidade.
- **Fluxo:**
  1. Pega os dados "reais" da API (Channel Statistics).
  2. Soma manualmente todos os vídeos no banco local.
  3. Compara os dois números e calcula a diverência (%).
  4. Gera um relatório de Aprovado/Reprovado.

---

## 🔍 Onde procurar erros?

Se você está vendo um número estranho, verifique o componente responsável:

| Sintoma | Culpado Provável | O que verificar |
| :--- | :--- | :--- |
| **"Canal não encontrado"** | `youtube_client.py` | Lógica de `resolve_channel_id` (Fallback de handle). |
| **"Views totais erradas"** | `db.py` | Método `create_snapshot` (ele que soma tudo). |
| **"Gráfico estranho"** | `main.py` | Lógica de normalização no `page_comparison`. |
| **"Vídeo faltando"** | `collector.py` | Lógica incremental (pode ter pulado vídeos antigos). |
| **"Erro de API/Quota"** | `.env` | Verifique se `YT_API_KEY` está válida. |

---

Este documento serve como mapa para qualquer manutenção futura.
