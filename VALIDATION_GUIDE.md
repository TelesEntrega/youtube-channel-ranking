# Validação Contra Vídeo Original

Guia para validar que o sistema gera rankings idênticos ao método manual do vídeo que inspirou este projeto.

---

## 🎯 Objetivo da Validação

**Provar que**: O ranking gerado automaticamente pelo sistema é **matematicamente idêntico** ao método manual mostrado no vídeo.

**Método do vídeo**:
- Somar `viewCount` de **TODOS os vídeos** do canal (incluindo Shorts)
- Ordenar canais por total de visualizações (descendente)
- Esse é o ranking "oficial"

**Nosso método**:
```sql
SELECT 
    c.title,
    SUM(v.last_view_count) as total_views
FROM channels c
JOIN videos v ON c.channel_id = v.channel_id
GROUP BY c.channel_id
ORDER BY total_views DESC;
```

---

## 📋 Metodologia de Validação

### Fase 1: Seleção de Canais Teste

Escolher **3 canais** com perfis diferentes:

1. **Canal Pequeno** (~100-500 vídeos)
   - Fácil de auditar manualmente
   - Paginação simples
   - Exemplo: `@gemini`, `@google`

2. **Canal Médio** (~500-2000 vídeos)
   - Teste de paginação robusta
   - Mix de Shorts e longos
   - Exemplo: `@TEDx`

3. **Canal Grande** (>2000 vídeos)
   - Stress test de paginação
   - Alto volume de Shorts
   - Exemplo: `@MrBeast`, `@DudePerfect`

### Fase 2: Coleta via Sistema

```bash
# 1. Adicionar canais via dashboard
streamlit run app/main.py

# ou via script Python
python -c "
from app.collector import Collector
from app.db import Database
from app.youtube_client import YouTubeClient
import os

db = Database()
yt = YouTubeClient(os.getenv('YT_API_KEY'))
collector = Collector(yt, db)

# Coletar em modo FULL (primeira vez)
canais = ['@gemini', '@TEDx', '@MrBeast']
for canal in canais:
    print(f'Coletando {canal}...')
    result = collector.collect_channel(canal, mode='full')
    print(result)
"
```

### Fase 3: Comparação Manual (Canal Pequeno)

**Passo a passo para validar manualmente**:

1. **Obter total reportado pela API**:
```python
# channels.list retorna statistics.viewCount
channel_info = youtube.channels().list(
    part='statistics',
    id='CHANNEL_ID'
).execute()
api_total = channel_info['items'][0]['statistics']['viewCount']
```

2. **Obter nosso total calculado**:
```sql
SELECT 
    c.title,
    SUM(v.last_view_count) as nossa_soma,
    COUNT(*) as total_videos
FROM channels c
JOIN videos v ON c.channel_id = v.channel_id
WHERE c.channel_id = 'CHANNEL_ID'
GROUP BY c.channel_id;
```

3. **Calcular divergência**:
```
diff = |nossa_soma - api_total| / api_total * 100
```

4. **Verificar contagem de vídeos**:
```python
channel_info['items'][0]['statistics']['videoCount']  # reportado
vs
nossa_query['total_videos']  # coletado
```

### Fase 4: Validação de Shorts

**Confirmar que Shorts estão sendo contabilizados**:

```sql
-- Shorts do canal
SELECT 
    COUNT(*) as total_shorts,
    SUM(last_view_count) as shorts_views
FROM videos
WHERE channel_id = 'CHANNEL_ID' AND is_short = 1;

-- Vídeos longos
SELECT 
    COUNT(*) as total_longos,
    SUM(last_view_count) as long_views
FROM videos
WHERE channel_id = 'CHANNEL_ID' AND is_short = 0;

-- Total deve bater
SELECT 
    SUM(last_view_count) as total_unified
FROM videos
WHERE channel_id = 'CHANNEL_ID';
-- Este valor deve ser usado no ranking
```

**Validar detecção de Shorts**:
```sql
-- Verificar que vídeos ≤60s estão marcados
SELECT video_id, title, duration_seconds, is_short
FROM videos
WHERE channel_id = 'CHANNEL_ID' AND duration_seconds <= 60
ORDER BY duration_seconds DESC
LIMIT 10;
```

### Fase 5: Teste de Ranking Ordenado

**Comparar ordem do ranking**:

```sql
-- Nosso ranking (top 10)
SELECT 
    RANK() OVER (ORDER BY SUM(v.last_view_count) DESC) as rank,
    c.title,
    SUM(v.last_view_count) as total_views
FROM channels c
JOIN videos v ON c.channel_id = v.channel_id
GROUP BY c.channel_id
ORDER BY total_views DESC
LIMIT 10;
```

**Comparar com vídeo / fonte externa**:
- Se o vídeo mostrou ranking específico, comparar posição por posição
- Divergências < 5% são aceitáveis (vídeos privados)
- **Ordem** deve ser idêntica (exceto empates)

---

## 🤖 Script de Validação Automática

Criado em: `scripts/validate_against_video.py`

**Uso**:
```bash
python scripts/validate_against_video.py CHANNEL_ID
```

**O que faz**:
1. Busca dados do canal via API (channel.statistics.viewCount)
2. Busca dados do nosso banco (soma de videos.last_view_count)
3. Compara divergência
4. Valida contagem de vídeos
5. Lista top 10 vídeos mais vistos
6. Mostra breakdown Shorts vs Long
7. Gera relatório de validação

**Output esperado**:
```
════════════════════════════════════════════════════════════
VALIDAÇÃO: Canal X
════════════════════════════════════════════════════════════

📊 Comparação de Totais:
   API (reported):     1,234,567,890 views
   Sistema (calculated): 1,230,000,000 views
   Divergência:        0.37% ✅

📹 Contagem de Vídeos:
   API (reported):     1,523 vídeos
   Sistema (collected): 1,520 vídeos
   Missing:            3 vídeos (0.2%) - provavelmente privados

🎬 Breakdown por Tipo:
   Shorts:  456 vídeos | 345M views (28%)
   Longos:  1,064 vídeos | 885M views (72%)

✅ RESULTADO: APROVADO
   - Divergência < 5%
   - Vídeos coletados > 95%
   - Shorts detectados corretamente
```

---

## 📊 Critérios de Aprovação

### ✅ APROVADO se:
- Divergência de total_views < 5%
- Vídeos coletados ≥ 95% do reportado
- Shorts identificados com precisão (duração ≤60s)
- Ordem de ranking preservada (top 10)

### ⚠️ INVESTIGAR se:
- Divergência entre 5-10%
- Vídeos coletados entre 90-95%
- Ordem de ranking tem inversões

### ❌ REPROVAR se:
- Divergência > 10%
- Vídeos coletados < 90%
- Falha em detectar Shorts
- Ordem de ranking incorreta

---

## 🔬 Casos de Teste Documentados

### Caso 1: Canal sem Shorts

**Canal**: (escolher um canal sem Shorts)  
**Expectativa**:
- `shorts_count = 0`
- `total_views = long_views`
- Divergência mínima

### Caso 2: Canal só com Shorts

**Canal**: (escolher um canal apenas de Shorts)  
**Expectativa**:
- `long_count = 0`
- `total_views = shorts_views`
- Todos vídeos com `duration_seconds <= 60`

### Caso 3: Canal Misto (Realista)

**Canal**: `@MrBeast`  
**Expectativa**:
- Mix de Shorts e longos
- Divergência < 3% (canal grande, alguns privados)
- Paginação completa (>1000 vídeos)

### Caso 4: Canal com Lives

**Canal**: (escolher canal com lives frequentes)  
**Expectativa**:
- Lives com `is_live = 1` NÃO contam como Shorts
- Lives passadas (gravadas) contam no total
- Lives `upcoming` são ignoradas

---

## 📸 Documentação de Provas

### Screenshots Recomendados:

1. **Comparação lado a lado**:
   - Nosso dashboard (ranking table)
   - vs Vídeo original (se disponível)
   - ou vs YouTube Channel Stats

2. **Query SQL com resultados**:
   ```sql
   SELECT ... -- screenshot do resultado
   ```

3. **Divergência auditada**:
   - Card de auditoria no dashboard
   - Mostrando diff_percent < 5%

4. **Top vídeos do canal**:
   - Comparar com YouTube real
   - Confirmar que o mais visto bate

---

## 🎥 Vídeo de Validação (Opcional)

Se quiser criar conteúdo público:

**Roteiro sugerido**:
1. Mostrar vídeo original que inspirou
2. Explicar método manual (soma de views)
3. Mostrar nosso sistema rodando
4. Executar script de validação ao vivo
5. Comparar resultados (divergência < 5%)
6. Mostrar dashboard com ranking
7. Conclusão: "sistema validado matematicamente"

**Timestamp sugerido**: 5-8 minutos

---

## 🔗 Próximos Passos Após Validação

### Se APROVADO (esperado):
- [ ] Documentar resultados no README
- [ ] Adicionar badges: "✅ Validated against YouTube API"
- [ ] Criar issue/changelog com provas
- [ ] Publicar (se aplicável)

### Se REPROVAR (improvável):
- [ ] Investigar causa raiz
- [ ] Corrigir bug identificado
- [ ] Re-testar
- [ ] Documentar lição aprendida

---

## 💡 Nota sobre Divergências Esperadas

**É NORMAL ter divergências de 1-5% porque**:

1. **Vídeos privados/unlisted**: API não lista, mas conta no total
2. **Vídeos deletados**: Removidos entre listagem e obtenção de stats
3. **Cache da API**: `channel.statistics.viewCount` pode ter delay
4. **Lives/Premieres**: Status muda, contagem varia

**Nosso sistema é mais preciso porque**:
- Soma vídeo por vídeo (auditável)
- Registra cada viewCount individual
- Transparente sobre o que foi incluído

👉 Divergências < 5% **provam que o sistema está correto**.

---

**Última atualização**: 2026-01-03  
**Status**: Metodologia aprovada para validação
