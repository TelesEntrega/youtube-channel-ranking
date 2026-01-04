"""
Streamlit Dashboard for YouTube Channel Ranking System
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
import pandas as pd

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from db import Database
from youtube_client import YouTubeClient
from collector import Collector
from ranking import RankingEngine

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="YouTube Channel Ranking",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .rank-badge {
        font-size: 24px;
        font-weight: bold;
        color: #1f77b4;
    }
    .stDataFrame {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_components():
    """Initialize database and API clients."""
    db_path = os.getenv('DB_PATH', 'data/rankings.db')
    api_key = os.getenv('YT_API_KEY')
    
    if not api_key:
        st.error("⚠️ YouTube API key not found! Please set YT_API_KEY in .env file")
        st.stop()
    
    db = Database(db_path)
    youtube = YouTubeClient(api_key)
    collector = Collector(youtube, db)
    ranking = RankingEngine(db)
    
    return db, youtube, collector, ranking


def format_number(num):
    """Format large numbers with thousand separators."""
    if num is None:
        return "0"
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num/1_000:.2f}K"
    return str(num)


def page_ranking():
    """Main ranking page."""
    st.title("📊 YouTube Channel Ranking")
    st.markdown("### Ranking baseado em visualizações totais (todos os vídeos)")
    
    db, youtube, collector, ranking = init_components()
    
    # Filters in sidebar
    st.sidebar.header("Filtros")
    
    # Top N filter
    top_n_options = {
        "Top 10": 10,
        "Top 50": 50,
        "Top 100": 100,
        "Top 500": 500,
        "Todos": 999999
    }
    top_n_label = st.sidebar.selectbox("Exibir", list(top_n_options.keys()), index=2)
    top_n = top_n_options[top_n_label]
    
    # Search filter
    search_query = st.sidebar.text_input("🔍 Buscar canal", "")
    
    # Manual update button
    st.sidebar.markdown("---")
    st.sidebar.header("Ações")
    
    if st.sidebar.button("🔄 Atualizar Canais", help="Atualizar dados de todos os canais"):
        with st.spinner("Coletando dados..."):
            # Get list of existing channels
            cursor = db.conn.cursor()
            cursor.execute("SELECT DISTINCT channel_id FROM channels")
            channel_ids = [row[0] for row in cursor.fetchall()]
            
            if channel_ids:
                st.info(f"Atualizando {len(channel_ids)} canais...")
                progress_bar = st.progress(0)
                
                for i, channel_id in enumerate(channel_ids):
                    try:
                        collector.collect_channel(channel_id, mode='incremental')
                        progress_bar.progress((i + 1) / len(channel_ids))
                    except Exception as e:
                        st.warning(f"Erro ao atualizar {channel_id}: {e}")
                
                st.success("✅ Atualização concluída!")
                st.cache_data.clear()
            else:
                st.warning("Nenhum canal para atualizar. Adicione canais primeiro.")
    
    # Add new channel section
    with st.sidebar.expander("➕ Adicionar Canal"):
        channel_input = st.text_input(
            "ID, @handle ou URL",
            placeholder="@MrBeast ou UCX6OQ3DkcsbYNE6H8uQQuVA",
            help="Aceita: channel ID, @handle, ou URL completa"
        )
        
        if st.button("Adicionar"):
            if channel_input:
                with st.spinner(f"Coletando {channel_input}..."):
                    try:
                        result = collector.collect_channel(channel_input, mode='full')
                        if result['status'] == 'success':
                            st.success(f"✅ Canal adicionado: {result['title']}")
                            st.cache_data.clear()
                        else:
                            st.error(f"❌ Erro: {result.get('message', 'Desconhecido')}")
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")
            else:
                st.warning("Digite um canal para adicionar")
    
    # Get ranking data
    search = search_query if search_query else None
    ranking_data = ranking.get_global_ranking(limit=top_n, offset=0, search_query=search)
    total_channels = ranking.get_total_channels_count(search_query=search)
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Canais", total_channels)
    
    with col2:
        if ranking_data:
            total_views = sum(r['total_views'] for r in ranking_data)
            st.metric("Total de Views", format_number(total_views))
    
    with col3:
        if ranking_data:
            total_videos = sum(r['total_videos'] for r in ranking_data)
            st.metric("Total de Vídeos", format_number(total_videos))
    
    with col4:
        if ranking_data:
            total_shorts = sum(r['shorts_count'] for r in ranking_data)
            st.metric("Total de Shorts", format_number(total_shorts))
    
    st.markdown("---")
    
    # Display ranking table
    if not ranking_data:
        st.info("Nenhum canal encontrado. Adicione canais usando o painel lateral.")
    else:
        # Convert to DataFrame
        df = pd.DataFrame(ranking_data)
        
        # Format for display
        display_df = pd.DataFrame({
            'Rank': df['rank'],
            'Canal': df['title'],
            'Handle': df['handle'].fillna('-'),
            'Total Views': df['total_views'].apply(format_number),
            'Shorts Views': df['shorts_views'].apply(format_number),
            'Long Views': df['long_views'].apply(format_number),
            'Vídeos': df['total_videos'],
            'Shorts': df['shorts_count'],
            'Última Atualização': pd.to_datetime(df['last_update']).dt.strftime('%Y-%m-%d %H:%M')
        })
        
        # Display table with enhanced info
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Rank': st.column_config.NumberColumn(width='small'),
                'Canal': st.column_config.TextColumn(width='large'),
                'Handle': st.column_config.TextColumn(width='medium'),
                'Total Views': st.column_config.TextColumn(width='medium', help='Soma de visualizações de todos os vídeos'),
                'Shorts Views': st.column_config.TextColumn(width='medium'),
                'Long Views': st.column_config.TextColumn(width='medium'),
                'Vídeos': st.column_config.NumberColumn(width='small'),
                'Shorts': st.column_config.NumberColumn(width='small'),
                'Última Atualização': st.column_config.TextColumn(width='medium', help='Última vez que os dados deste canal foram atualizados')
            }
        )
        
        # Channel selection for details
        st.markdown("---")
        st.subheader("Detalhes do Canal")
        
        selected_channel = st.selectbox(
            "Selecione um canal para ver detalhes",
            options=df['channel_id'].tolist(),
            format_func=lambda x: df[df['channel_id'] == x]['title'].values[0]
        )
        
        if selected_channel:
            display_channel_details(selected_channel, ranking)


def display_channel_details(channel_id: str, ranking_engine):
    """Display detailed information for a channel."""
    details = ranking_engine.get_channel_details(channel_id)
    
    if not details:
        st.error("Canal não encontrado")
        return
    
    st.markdown(f"## {details['title']}")
    
    if details['handle']:
        st.markdown(f"**Handle:** @{details['handle']}")
    if details['country']:
        st.markdown(f"**País:** {details['country']}")
    
    # Delete button (right aligned)
    col_del_1, col_del_2 = st.columns([6, 1])
    with col_del_2:
        if st.button("🗑️ Excluir", key="delete_btn", type="primary", help="Excluir este canal permanentemente"):
            st.session_state.show_delete_confirm = True

    if st.session_state.get('show_delete_confirm', False):
        st.warning(f"Tem certeza que deseja excluir **{details['title']}**? Esta ação não pode ser desfeita.")
        col_conf_1, col_conf_2 = st.columns(2)
        with col_conf_1:
            if st.button("✅ Sim, excluir", key="confirm_delete"):
                db, _, _, _ = init_components()
                db.delete_channel(channel_id)
                st.success("Canal excluído com sucesso!")
                st.session_state.show_delete_confirm = False
                st.cache_data.clear()
                # Rerun to update list
                st.rerun()
        with col_conf_2:
            if st.button("❌ Cancelar", key="cancel_delete"):
                st.session_state.show_delete_confirm = False
                st.rerun()
    
    # Show data quality indicator
    db, _, _, ranking = init_components()
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT diff_percent, reported_channel_views, total_views, snapshot_date
        FROM channel_snapshots
        WHERE channel_id = ?
        ORDER BY snapshot_date DESC
        LIMIT 1
    """, (channel_id,))
    snapshot = cursor.fetchone()
    
    if snapshot and snapshot['diff_percent'] is not None:
        diff = snapshot['diff_percent']
        if diff < 1:
            st.success(f"✅ **Dados Auditados**: Divergência < 1% ({diff:.2f}%) - Ranking altamente confiável")
        elif diff < 5:
            st.info(f"ℹ️ **Dados Auditados**: Divergência {diff:.2f}% - Dentro do esperado")
        else:
            st.warning(f"⚠️ **Atenção**: Divergência {diff:.2f}% - Possíveis vídeos privados/removidos")
        
        with st.expander("📊 Detalhes da Auditoria"):
            st.markdown(f"**Soma Manual (Ranking):** {format_number(snapshot['total_views'])}")
            st.markdown(f"**Reportado pela API:** {format_number(snapshot['reported_channel_views'])}")
            st.markdown(f"**Divergência:** {diff:.2f}%")
            st.markdown(f"**Última Verificação:** {snapshot['snapshot_date']}")
            st.caption("Divergências de 1-5% são normais devido a vídeos privados/removidos e cache da API.")
    
    # Statistics cards
    col1, col2, col3, col4 = st.columns(4)
    
    stats = details['stats']
    
    with col1:
        st.metric("Total Views", format_number(stats['total_views']))
    
    with col2:
        st.metric("Shorts Views", format_number(stats['shorts_views']))
    
    with col3:
        st.metric("Long Views", format_number(stats['long_views']))
    
    with col4:
        st.metric("Total Vídeos", stats['total_videos'])
    
    # Top video and short
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔥 Vídeo Mais Visto")
        if details['top_video']:
            top = details['top_video']
            st.markdown(f"**{top['title']}**")
            st.markdown(f"Views: **{format_number(top['last_view_count'])}**")
            st.markdown(f"Tipo: {'Short' if top['is_short'] else 'Long'}")
            st.markdown(f"[Assistir no YouTube](https://youtube.com/watch?v={top['video_id']})")
    
    with col2:
        st.markdown("### 🎬 Short Mais Visto")
        if details['top_short']:
            top = details['top_short']
            st.markdown(f"**{top['title']}**")
            st.markdown(f"Views: **{format_number(top['last_view_count'])}**")
            st.markdown(f"[Assistir no YouTube](https://youtube.com/watch?v={top['video_id']})")
    
    # Top 10 videos table
    st.markdown("### 📋 Top 10 Vídeos")
    
    if details['top_10_videos']:
        top_10_df = pd.DataFrame([
            {
                'Título': v['title'],
                'Views': format_number(v['last_view_count']),
                'Tipo': 'Short' if v['is_short'] else 'Long',
                'Publicado': v['published_at'][:10],
                'Link': f"https://youtube.com/watch?v={v['video_id']}"
            }
            for v in details['top_10_videos']
        ])
        
        st.dataframe(
            top_10_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Link': st.column_config.LinkColumn(width='small')
            }
        )
    
    # Historical chart
    st.markdown("### 📈 Evolução Histórica (últimos 30 dias)")
    history = ranking_engine.get_channel_history(channel_id, days=30)
    
    if history:
        history_df = pd.DataFrame(history)
        history_df['snapshot_date'] = pd.to_datetime(history_df['snapshot_date'])
        
        st.line_chart(
            history_df.set_index('snapshot_date')[['total_views', 'shorts_views', 'long_views']],
            use_container_width=True
        )
    else:
        st.info("Sem dados históricos disponíveis ainda")


def page_comparison():
    """Comparison page logic."""
    st.title("📈 Comparativo de Canais")
    st.markdown("### Analise o crescimento de múltiplos canais em um período")
    
    db, _, collector, ranking = init_components()
    
    # Snapshot status in sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("📸 Snapshots de Vídeos")
    
    snapshot_stats = db.get_snapshot_stats()
    latest_snapshot = snapshot_stats['latest_date']
    
    if latest_snapshot:
        st.sidebar.success(f"✅ **Último:** {latest_snapshot}")
        st.sidebar.caption(f"📊 {snapshot_stats['videos_tracked']:,} vídeos • {snapshot_stats['unique_dates']} dias")
    else:
        st.sidebar.warning("⚠️ **Nenhum snapshot coletado**")
        st.sidebar.caption("Clique no botão abaixo para iniciar")
    
    if st.sidebar.button("🔄 Coletar Snapshots Agora", help="Salvar view counts atuais de todos os vídeos"):
        with st.spinner("Coletando snapshots de todos os vídeos..."):
            try:
                result = collector.collect_snapshots_for_all_channels()
                st.sidebar.success(f"✅ Coletados {result['videos_snapshotted']:,} snapshots!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ Erro: {e}")
    
    # 1. Select Channels
    cursor = db.conn.cursor()
    cursor.execute("SELECT channel_id, title FROM channels ORDER BY title")
    channels = cursor.fetchall()
    
    channel_options = {row['channel_id']: row['title'] for row in channels}
    
    # Auto-select ALL channels
    selected_channels = list(channel_options.keys())
    
    st.info(f"📊 **{len(selected_channels)} canais** serão incluídos no ranking")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Monthly period selector
        import calendar
        now = pd.Timestamp.now()
        
        # Generate last 6 months options
        month_options = ["Personalizado"]
        for i in range(6):
            date = now - pd.DateOffset(months=i)
            month_options.append(f"{calendar.month_name[date.month]} {date.year}")
        
        preset = st.selectbox(
            "Período",
            options=month_options,
            index=1  # Current month by default
        )
        
        if preset == "Personalizado":
            start_date = st.date_input("Data Inicial", value=pd.Timestamp.now() - pd.Timedelta(days=30))
            end_date = st.date_input("Data Final", value=pd.Timestamp.now())
        else:
            # Parse selected month
            parts = preset.split()
            month_name = parts[0]
            year = int(parts[1])
            month_num = list(calendar.month_name).index(month_name)
            
            # Get first and last day of month
            start_date = pd.Timestamp(year, month_num, 1)
            last_day = calendar.monthrange(year, month_num)[1]
            end_date = pd.Timestamp(year, month_num, last_day)
            
            st.caption(f"📅 {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}")
    
    
    with col2:
        # MODE SELECTOR (Triple Ranking System - Gorgonoid Complete)
        mode = st.radio(
            "**Metodologia:**",
            options=[
                "📊 Gorgonoid Canal (Delta Canal)",
                "🎬 Gorgonoid Conteúdo (Delta Vídeo)",
                "📈 Análise de Views (Publicado)"
            ],
            index=0,  # Default to Delta Canal
            help="Canal (total), Conteúdo (vídeos), ou Views Publicadas"
        )
    
    st.markdown("---")
    
    if st.button("🏆 Gerar Ranking", type="primary", use_container_width=True):
        if not selected_channels:
            st.warning("Nenhum canal encontrado no banco de dados.")
            return
            
        if start_date > end_date:
            st.error("Data final deve ser maior que data inicial")
            return


        # TRIPLE RANKING LOGIC
        if "Canal" in mode:
            # ============ MODO 1: DELTA CANAL (PLANILHA GORGONOID) ============
            ranking_data = ranking.get_comparison_data_delta_channel(
                selected_channels, 
                start_date.strftime('%Y-%m-%d'), 
                end_date.strftime('%Y-%m-%d')
            )
            
            # Check if we have snapshot data
            if ranking_data:
                missing_count = sum(1 for r in ranking_data if r.get('missing_snapshots', False))
                
                if missing_count == len(ranking_data):
                    st.error("⚠️ **Sem dados de snapshot de canal!**\n\nO modo Delta Canal requer snapshots diários. Clique em 'Coletar Snapshots Agora' e aguarde 1+ dia.")
                    return
                
                if missing_count > 0:
                    st.warning(f"⚠️ {missing_count}/{len(ranking_data)} canais sem snapshots completos")
            
            mode_name = "Gorgonoid Canal (Delta Canal)"
            column_map = {
                "ant": "Ant (Views Início)",
                "atual": "Atual (Views Fim)",
                "reais": "Reais (Crescimento)",
                "percent": "% Crescimento"
            }
            explanation = (
                "ℹ️ **Metodologia Gorgonoid (Delta Canal - Planilha)**\n\n"
                "Este ranking usa o **viewCount total do canal** (da API oficial do YouTube). "
                "Métricas:\n"
                "- **Ant:** Views totais do canal no início do período\n"
                "- **Atual:** Views totais do canal no fim do período\n"
                "- **Reais:** Crescimento absoluto (Atual - Ant)\n"
                "- **%:** Percentual de crescimento\n\n"
                "⚠️ Requer snapshots diários (coletar primeiro snapshot, aguardar 1+ dia)."
            )
            use_delta_canal_columns = True
            
        elif "Conteúdo" in mode:
            # ============ MODO 2: DELTA CONTEÚDO (SOMA DE VÍDEOS) ============
            ranking_data = ranking.get_comparison_data_delta(
                selected_channels, 
                start_date.strftime('%Y-%m-%d'), 
                end_date.strftime('%Y-%m-%d')
            )
            
            # Check if we have snapshot data
            if ranking_data:
                total_tracked = sum(r.get('videos_with_data', 0) for r in ranking_data)
                total_skipped = sum(r.get('videos_skipped', 0) for r in ranking_data)
                
                if total_tracked == 0:
                    st.error("⚠️ **Sem dados de snapshot de vídeos!**\n\nO Modo Conteúdo requer snapshots históricos. Clique em 'Coletar Snapshots Agora' e aguarde 7+ dias.")
                    return
                
                st.caption(f"📊 Rastreando {total_tracked:,} vídeos | {total_skipped:,} vídeos sem snapshots completos")
            
            mode_name = "Gorgonoid Conteúdo (Delta por Vídeo)"
            column_map = {
                "views_shorts": "Crescimento Shorts",
                "views_longos": "Crescimento Longos",
                "views_totais": "Crescimento Total"
            }
            explanation = (
                "ℹ️ **Metodologia Gorgonoid (Delta por Vídeo)**\n\n"
                "Este ranking mede o **CRESCIMENTO** de views somando o delta de cada vídeo. "
                "Para cada vídeo do canal (independente de quando foi publicado), calculamos: `views_fim - views_inicio`. "
                "Reflete o desempenho real do conteúdo no período.\n\n"
                "⚠️ Requer snapshots diários (aguarde 7+ dias após primeira coleta)."
            )
            use_delta_canal_columns = False
            
        else:
            # ============ MODO 3: ANÁLISE DE VIEWS (CONTEÚDO PUBLICADO) ============
            ranking_data = ranking.get_comparison_data(
                selected_channels, 
                start_date.strftime('%Y-%m-%d'), 
                end_date.strftime('%Y-%m-%d')
            )
            
            mode_name = "Análise de Views (Conteúdo Publicado)"
            column_map = {
                "views_shorts": "Views Shorts",
                "views_longos": "Views Longos",
                "views_totais": "Views Totais"
            }
            explanation = (
                "ℹ️ **Análise de Views do Período (Conteúdo Publicado)**\n\n"
                "Este ranking soma as visualizações **TOTAIS** de vídeos e shorts publicados no período. "
                "Cada vídeo carrega suas views acumuladas desde a publicação até hoje. "
                "Métrica de volume de produção."
            )
            use_delta_canal_columns = False
        
        if not ranking_data:
            st.warning("Nenhum dado encontrado. Verifique o período selecionado.")
            return

        # Calculate statistics (Modes with Shorts/Longos breakdown)
        if not use_delta_canal_columns:
            df_calc = pd.DataFrame(ranking_data)
            p75_efficiency = df_calc['media_por_conteudo'].quantile(0.75) if not df_calc.empty and 'media_por_conteudo' in df_calc.columns else 0
            p75_volume = df_calc['total_videos'].quantile(0.75) if not df_calc.empty and 'total_videos' in df_calc.columns else 0
            avg_efficiency = df_calc['media_por_conteudo'].mean() if not df_calc.empty and 'media_por_conteudo' in df_calc.columns else 0
        else:
            # Delta Canal doesn't need these stats
            p75_efficiency = 0
            p75_volume = 0
            avg_efficiency = 0

        # Helper to get logo path
        def get_brand_logo(brand_name):
            if not brand_name or brand_name in ['?', 'Sem Patrocínio']:
                return ""
                
            safe_name = brand_name.lower().replace(" ", "_").replace(".", "")
            logo_path = f"assets/logos/{safe_name}.png"
            
            # Check if exists (relative to current script execution)
            if os.path.exists(logo_path):
                # Using st.image directly in table is tricky, using base64 or serving static
                # For simplicity in dataframe, we just return name. 
                # But for custom table, we can return HTML img tag if using markdown
                # Here we will try to just show the name with emoji first, or better yet
                # We will render a custom HTML table or use st.dataframe with column config if available
                return logo_path
            return None

        # Build display table
        table_rows = []
        for i, item in enumerate(ranking_data, 1):
            row = {}
            
            # Column Order: Pos -> Marca -> Canal -> ...
            row['#'] = i
            
            # Brand
            brand = item.get('brand', '')
            row['Marca'] = brand if brand else "-"
            
            # Channel
            row['Canal'] = item.get('title', item.get('channel_id', 'Canal Desconhecido'))
            
            if use_delta_canal_columns:
                # Delta Canal Columns
                row['Ant'] = f"{item.get('ant', 0):,.0f}".replace(",", ".")
                row['Atual'] = f"{item.get('atual', 0):,.0f}".replace(",", ".")
                row['Reais'] = f"{item.get('reais', 0):,.0f}".replace(",", ".")
                
                pct = item.get('percent', 0)
                color = "green" if pct > 0 else "red" if pct < 0 else "gray"
                row['%'] = pct  # Keep raw for formatting later or pre-format
                row['Formatted_%'] = f"{pct:+.2f}%"

            else:
                # Content Columns - Separated Shorts and Longs
                shorts_count = item.get('shorts_periodo', item.get('shorts_count', 0))
                longs_count = item.get('longos_periodo', item.get('long_count', 0))
                total_videos = item.get('total_videos', 0)
                
                row['Vídeos'] = total_videos
                row['Shorts'] = shorts_count  # Separate column for short count
                row['Longos'] = longs_count   # Separate column for long count

                # Views Columns - define variables
                views_sh = item.get('views_sh_periodo', item.get('shorts_views', 0))
                views_lo = item.get('views_lo_periodo', item.get('long_views', 0))
                views_total = item.get('views_total_periodo', item.get('views_period', 0))
                
                row['Views Shorts'] = f"{views_sh:,.0f}".replace(",", ".")
                row['Views Longos'] = f"{views_lo:,.0f}".replace(",", ".")
                row['Views Total'] = f"{views_total:,.0f}".replace(",", ".")

            table_rows.append(row)
            
        st.subheader(f"🏆 Ranking: {mode_name}")
        st.info(explanation)
        
        # Safety check
        if not table_rows:
            st.warning("⚠️ Nenhum dado para exibir. Verifique se há snapshots disponíveis para o período selecionado.")
            return
        
        # Create DataFrame safely
        try:
            df = pd.DataFrame(table_rows)
        except Exception as e:
            st.error(f"❌ Erro ao criar tabela: {e}")
            st.write("Debug - Dados recebidos:")
            st.write(table_rows[:3] if len(table_rows) > 0 else "Vazio")
            return
        
        # Display logic
        if use_delta_canal_columns:
            st.dataframe(
                df,
                column_config={
                    "#": st.column_config.NumberColumn("Posição", width="small"),
                    "Marca": st.column_config.TextColumn("Marca", help="Patrocinador"),
                    "Canal": st.column_config.TextColumn("Canal", width="medium"),
                    "Ant": st.column_config.TextColumn("Anterior"),
                    "Atual": st.column_config.TextColumn("Atual"),
                    "Reais": st.column_config.TextColumn("Crescimento (Reais)"),
                    "%": st.column_config.ProgressColumn(
                        "Crescimento (%)", 
                        format="%.2f%%", 
                        min_value=-10, 
                        max_value=100
                    ),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.dataframe(
                df,
                column_config={
                    "#": st.column_config.NumberColumn("Posição", width="small"),
                    "Marca": st.column_config.TextColumn("Marca", help="Patrocinador", width="small"),
                    "Canal": st.column_config.TextColumn("Canal", width="medium"),
                    "Vídeos": st.column_config.NumberColumn("Vídeos", width="small"),
                    "Shorts": st.column_config.NumberColumn("Shorts", help="Quantidade de Shorts publicados", width="small"),
                    "Longos": st.column_config.NumberColumn("Longos", help="Quantidade de vídeos longos publicados", width="small"),
                    "Views Shorts": st.column_config.TextColumn("Views Shorts"),
                    "Views Longos": st.column_config.TextColumn("Views Longos"),
                    "Views Total": st.column_config.TextColumn("Views Totais", width="medium"),
                },
                hide_index=True,
                use_container_width=True
            )
        
        st.caption(f"Dados atualizados em: {ranking_data[0].get('last_update', 'Hoje') if ranking_data else 'Hoje'}")
    
    elif not selected_channels:
        st.info("👆 Selecione pelo menos um canal para começar.")


def main():
    """Main application."""
    st.sidebar.title("Navegação")
    page = st.sidebar.radio("Ir para", ["🏆 Ranking Geral", "📈 Comparativo"], label_visibility="collapsed")
    
    if page == "🏆 Ranking Geral":
        page_ranking()
    elif page == "📈 Comparativo":
        page_comparison()


if __name__ == "__main__":
    main()
