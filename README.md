# YouTube Channel Ranking (Metodologia Gorgonoid)

Sistema de análise e ranking de canais do YouTube focado em crescimento real (delta de views) e volume de produção, replicando a metodologia Gorgonoid.

## 🎯 Objetivo

Monitorar canais concorrentes ou do mesmo nicho, identificando tendências de crescimento vs. volume de postagem, com suporte a análises detalhadas de Shorts vs. Vídeos Longos.

## 📊 Metodologias de Ranking

O sistema implementa **DUAS metodologias distintas**, selecionáveis via interface:

### 1. 📊 Modo Gorgonoid (Crescimento Real)
- **Foco:** Performance e momentum.
- **Métrica:** `Delta = Views no Fim - Views no Início`.
- **Como funciona:** Rastrea o crescimento de visualizações de **TODOS** os vídeos do canal durante o período, independentemente da data de publicação.
- **Requisição:** Precisa de snapshots diários (histórico criado dia-a-dia).
- **Ideal para:** Saber quem está crescendo mais, viralizando vídeos antigos ou novos.

### 2. 📈 Análise de Views do Período (Conteúdo Publicado)
- **Foco:** Volume de produção e entrega imediata.
- **Métrica:** Soma de views de vídeos **publicados** dentro do período.
- **Como funciona:** Filtra uploads pela data e soma suas views totais acumuladas.
- **Requisição:** Funciona imediatamente (sem necessidade de histórico prévio).
- **Ideal para:** Analisar o desempenho dos uploads de um mês específico.

## 🧠 Arquitetura

```
/
├── app/
│   ├── collector.py    # Coleta de dados da API do YouTube
│   ├── db.py           # Gerenciamento do SQLite (Snapshots e Vídeos)
│   ├── main.py         # Interface Streamlit (Dashboards)
│   ├── ranking.py      # Lógica de cálculo dos rankings
│   ├── utils.py        # Utilitários de formatação
│   └── youtube_client.py # Wrapper da API do YouTube
├── data/               # Banco de dados SQLite (rankings.db) - NÃO VERSIONADO
├── scripts/            # Scripts de automação (coleta diária, validação)
└── requirements.txt    # Dependências do projeto
```

## 🚀 Como Rodar Localmente

### 1. Requisitos
- Python 3.8+
- Chave de API do YouTube (Google Cloud Console)

### 2. Instalação

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/youtube-channel-ranking.git
cd youtube-channel-ranking

# Crie e ative o ambiente virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### 3. Configuração
Crie um arquivo `.env` baseado no `.env.example`:

```ini
YT_API_KEY=sua_chave_aqui
DB_PATH=data/rankings.db
```

### 4. Executando

**Iniciar a Interface Gráfica:**
```bash
streamlit run app/main.py
```

**Coleta de Snapshots (Diária):**
```bash
python scripts/collect_snapshots.py
```

## ⏱️ Coletor Diário

Para que o **Modo Gorgonoid** funcione, o sistema precisa tirar uma "foto" (snapshot) das visualizações de todos os vídeos pelo menos uma vez por dia.

**Agendamento Recomendado:**
- **Windows:** Task Scheduler rodando `scripts/collect_snapshots.py` às 00:00.
- **Linux:** Crontab (`0 0 * * * python scripts/collect_snapshots.py`).

## ⚠️ Observações Importantes

- **Histórico:** Ao iniciar o projeto, o Modo Gorgonoid precisará de pelo menos **1 dia** de intervalo (2 snapshots) para começar a mostrar dados, e **7 dias** para análises semanais consistentes.
- **Quotas:** O coletor otimiza chamadas de API, mas monitore sua cota diária do YouTube (padrão 10.000 unidades).

---

**Licença:** Privado / Proprietário.
