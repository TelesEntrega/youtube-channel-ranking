"""
Script de validação automática para comparar ranking gerado vs dados reais da API.
Uso: python scripts/validate_against_video.py CHANNEL_ID_OR_HANDLE
"""
import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from db import Database
from youtube_client import YouTubeClient
from dotenv import load_dotenv

load_dotenv()


def format_number(num):
    """Format large numbers with separators."""
    if num >= 1_000_000_000:
        return f"{num:,} ({num/1_000_000_000:.2f}B)"
    elif num >= 1_000_000:
        return f"{num:,} ({num/1_000_000:.2f}M)"
    return f"{num:,}"


def validate_channel(channel_input):
    """
    Validate a channel against YouTube API official data.
    
    Returns validation report with:
    - Total views comparison (API vs our calculation)
    - Video count comparison
    - Shorts breakdown
    - Divergence percentage
    - PASS/FAIL verdict
    """
    print("=" * 70)
    print(f"VALIDAÇÃO: {channel_input}")
    print("=" * 70)
    print()
    
    # Initialize components
    api_key = os.getenv('YT_API_KEY')
    if not api_key:
        print("❌ ERRO: YT_API_KEY não encontrada no .env")
        return
    
    db = Database()
    yt = YouTubeClient(api_key)
    
    # Resolve channel ID
    print("🔍 Resolvendo channel ID...")
    channel_id = yt.resolve_channel_id(channel_input)
    if not channel_id:
        print(f"❌ ERRO: Não foi possível resolver '{channel_input}'")
        return
    print(f"   ✓ Channel ID: {channel_id}")
    print()
    
    # Get channel metadata from API
    print("📡 Buscando dados oficiais da API...")
    metadata = yt.get_channel_metadata(channel_id)
    if not metadata:
        print(f"❌ ERRO: Canal não encontrado na API")
        return
    
    api_view_count = metadata['view_count']
    api_video_count = metadata['video_count']
    
    print(f"   ✓ Canal: {metadata['title']}")
    print(f"   ✓ Total Views (API): {format_number(api_view_count)}")
    print(f"   ✓ Total Vídeos (API): {api_video_count:,}")
    print()
    
    # Get our calculated data from database
    print("💾 Buscando dados calculados do sistema...")
    cursor = db.conn.cursor()
    
    # Check if channel exists in DB
    cursor.execute("SELECT channel_id FROM channels WHERE channel_id = ?", (channel_id,))
    if not cursor.fetchone():
        print(f"⚠️  Canal não encontrado no banco de dados")
        print(f"   Execute: python -c \"from app.collector import Collector; from app.db import Database; from app.youtube_client import YouTubeClient; import os; db = Database(); yt = YouTubeClient(os.getenv('YT_API_KEY')); c = Collector(yt, db); print(c.collect_channel('{channel_input}', mode='full'))\"")
        return
    
    # Get calculated stats
    stats = db.get_channel_stats(channel_id)
    calculated_views = stats['total_views']
    collected_videos = stats['total_videos']
    shorts_views = stats['shorts_views']
    long_views = stats['long_views']
    shorts_count = stats['shorts_videos']
    long_count = stats['long_videos']
    
    print(f"   ✓ Total Views (Calculado): {format_number(calculated_views)}")
    print(f"   ✓ Total Vídeos (Coletados): {collected_videos:,}")
    print()
    
    # Calculate divergences
    view_divergence = abs(calculated_views - api_view_count) / api_view_count * 100 if api_view_count > 0 else 0
    video_missing = api_video_count - collected_videos
    video_coverage = (collected_videos / api_video_count * 100) if api_video_count > 0 else 0
    
    # Print comparison
    print("📊 COMPARAÇÃO DE TOTAIS:")
    print(f"   API (reported):          {format_number(api_view_count)}")
    print(f"   Sistema (calculated):    {format_number(calculated_views)}")
    print(f"   Diferença absoluta:      {format_number(abs(calculated_views - api_view_count))}")
    print(f"   Divergência:             {view_divergence:.2f}%", end="")
    
    if view_divergence < 1:
        print(" ✅ EXCELENTE")
    elif view_divergence < 5:
        print(" ✅ BOM")
    elif view_divergence < 10:
        print(" ⚠️  ACEITÁVEL")
    else:
        print(" ❌ ALTO")
    print()
    
    print("📹 CONTAGEM DE VÍDEOS:")
    print(f"   API (reported):          {api_video_count:,} vídeos")
    print(f"   Sistema (collected):     {collected_videos:,} vídeos")
    print(f"   Missing:                 {video_missing:,} vídeos ({100-video_coverage:.1f}%)", end="")
    
    if video_coverage >= 99:
        print(" ✅")
    elif video_coverage >= 95:
        print(" ✅ (normal)")
    elif video_coverage >= 90:
        print(" ⚠️")
    else:
        print(" ❌")
    print()
    
    print("🎬 BREAKDOWN POR TIPO:")
    shorts_pct = (shorts_views / calculated_views * 100) if calculated_views > 0 else 0
    long_pct = (long_views / calculated_views * 100) if calculated_views > 0 else 0
    print(f"   Shorts:  {shorts_count:,} vídeos | {format_number(shorts_views)} ({shorts_pct:.1f}%)")
    print(f"   Longos:  {long_count:,} vídeos | {format_number(long_views)} ({long_pct:.1f}%)")
    print()
    
    # Top videos
    print("🏆 TOP 5 VÍDEOS MAIS VISTOS:")
    cursor.execute("""
        SELECT title, last_view_count, is_short, duration_seconds
        FROM videos
        WHERE channel_id = ?
        ORDER BY last_view_count DESC
        LIMIT 5
    """, (channel_id,))
    
    for i, row in enumerate(cursor.fetchall(), 1):
        tipo = "📱 Short" if row['is_short'] else "🎥 Long"
        print(f"   {i}. {tipo} - {format_number(row['last_view_count'])} views")
        print(f"      {row['title'][:60]}...")
    print()
    
    # Verdict
    print("=" * 70)
    print("📋 RESULTADO DA VALIDAÇÃO:")
    print()
    
    passed = True
    reasons = []
    
    # Check divergence
    if view_divergence < 5:
        print("   ✅ Divergência de views < 5%")
    elif view_divergence < 10:
        print("   ⚠️  Divergência de views entre 5-10% (investigar)")
        reasons.append(f"Divergência alta ({view_divergence:.2f}%)")
    else:
        print("   ❌ Divergência de views > 10% (FALHA)")
        passed = False
        reasons.append(f"Divergência crítica ({view_divergence:.2f}%)")
    
    # Check video coverage
    if video_coverage >= 95:
        print("   ✅ Vídeos coletados ≥ 95%")
    elif video_coverage >= 90:
        print("   ⚠️  Vídeos coletados entre 90-95% (investigar)")
        reasons.append(f"Cobertura baixa ({video_coverage:.1f}%)")
    else:
        print("   ❌ Vídeos coletados < 90% (FALHA)")
        passed = False
        reasons.append(f"Muitos vídeos faltando ({100-video_coverage:.1f}%)")
    
    # Check Shorts detection
    cursor.execute("""
        SELECT COUNT(*) as shorts_over_60
        FROM videos
        WHERE channel_id = ? AND is_short = 1 AND duration_seconds > 60
    """, (channel_id,))
    shorts_over_60 = cursor.fetchone()['shorts_over_60']
    
    if shorts_over_60 == 0:
        print("   ✅ Shorts detectados corretamente (todos ≤60s)")
    else:
        print(f"   ❌ {shorts_over_60} Shorts com duração >60s (erro de detecção)")
        passed = False
        reasons.append(f"Shorts mal identificados ({shorts_over_60})")
    
    print()
    print("-" * 70)
    
    if passed:
        print("   🎉 VALIDAÇÃO: APROVADO ✅")
        print()
        print("   O sistema está gerando rankings matematicamente corretos!")
        print("   Divergências são normais devido a vídeos privados/removidos.")
    else:
        print("   ❌ VALIDAÇÃO: REPROVADO")
        print()
        print("   Problemas encontrados:")
        for reason in reasons:
            print(f"   - {reason}")
        print()
        print("   Ação recomendada: Investigar logs e re-coletar canal.")
    
    print("=" * 70)
    
    db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/validate_against_video.py CHANNEL_ID_OR_HANDLE")
        print()
        print("Exemplos:")
        print("  python scripts/validate_against_video.py @MrBeast")
        print("  python scripts/validate_against_video.py UCX6OQ3DkcsbYNE6H8uQQuVA")
        print("  python scripts/validate_against_video.py https://youtube.com/@gemini")
        sys.exit(1)
    
    channel_input = sys.argv[1]
    validate_channel(channel_input)
