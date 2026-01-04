"""
Script de importação em lote - Adicionar múltiplos canais de uma vez
Uso: python scripts/bulk_import.py
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from dotenv import load_dotenv
from db import Database
from youtube_client import YouTubeClient
from collector import Collector

# Load environment
load_dotenv()

def main():
    print("=" * 70)
    print(" YouTube Ranking - Importação em Lote")
    print("=" * 70)
    print()
    
    # Carregar lista de canais
    channels_file = Path(__file__).parent.parent / 'canais.txt'
    
    if not channels_file.exists():
        print("❌ ERRO: Arquivo 'canais.txt' não encontrado!")
        print()
        print("Como criar:")
        print("1. Crie um arquivo chamado 'canais.txt' na raiz do projeto")
        print("2. Adicione 1 canal por linha (ID, @handle ou URL)")
        print()
        print("Exemplo:")
        print("  @cariani")
        print("  @bitelo")
        print("  UCxxxxxxxxxxxx")
        print("  https://youtube.com/@canal")
        print()
        return 1
    
    # Ler canais
    print(f"📄 Lendo arquivo: {channels_file}")
    channels = []
    
    with open(channels_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Ignorar linhas vazias e comentários
            if not line or line.startswith('#'):
                continue
            
            # Parse: aceita "Nome - URL" ou só "URL"
            if ' - ' in line:
                # Formato: "Gorgonoid - https://youtube.com/@Gorgonoid"
                parts = line.split(' - ', 1)
                channel_input = parts[1].strip()
                print(f"  Linha {line_num}: {parts[0].strip()} → {channel_input}")
            else:
                # Formato simples: "@cariani" ou "UCxxxx"
                channel_input = line
                print(f"  Linha {line_num}: {channel_input}")
            
            channels.append(channel_input)
    
    if not channels:
        print("❌ ERRO: Arquivo vazio ou sem canais válidos!")
        return 1
    
    print()
    print(f"✅ Total: {len(channels)} canais")
    print()
    
    # Confirmar
    print("Canais a importar:")
    for i, ch in enumerate(channels, 1):
        print(f"  {i}. {ch}")
    print()
    
    response = input("Continuar com a importação? (S/N): ")
    if response.upper() not in ['S', 'Y', 'SIM', 'YES']:
        print("❌ Importação cancelada pelo usuário")
        return 0
    
    print()
    print("=" * 70)
    print(" Iniciando Importação")
    print("=" * 70)
    print()
    
    # Inicializar componentes
    api_key = os.getenv('YT_API_KEY')
    if not api_key:
        print("❌ ERRO: YT_API_KEY não encontrada no .env")
        return 1
    
    db = Database('data/rankings.db')
    youtube = YouTubeClient(api_key)
    collector = Collector(youtube, db)
    
    # Importar canais
    successful = 0
    failed = 0
    
    for i, channel_input in enumerate(channels, 1):
        print(f"[{i}/{len(channels)}] Coletando: {channel_input}")
        
        try:
            result = collector.collect_channel(channel_input, mode='full')
            
            if result['status'] == 'success':
                successful += 1
                print(f"  ✅ {result['title']}: {result['videos_collected']} vídeos")
            else:
                failed += 1
                print(f"  ❌ Falhou: {result.get('message', 'Erro desconhecido')}")
        
        except Exception as e:
            failed += 1
            print(f"  ❌ Exceção: {e}")
        
        print()
    
    # Resumo
    print("=" * 70)
    print(" Importação Concluída")
    print("=" * 70)
    print()
    print(f"✅ Sucesso: {successful}/{len(channels)}")
    print(f"❌ Falhas:  {failed}/{len(channels)}")
    print()
    
    # Coletar snapshots
    if successful > 0:
        print("=" * 70)
        print(" Coletando Snapshots Iniciais")
        print("=" * 70)
        print()
        
        snapshot_result = collector.collect_snapshots_for_all_channels()
        
        print()
        print("📊 Snapshots:")
        print(f"  Vídeos: {snapshot_result['videos_snapshotted']}")
        print(f"  Canais: {snapshot_result['channels_snapshotted']}")
        print()
    
    # Fechar
    db.close()
    
    print("=" * 70)
    print(" ✅ PROCESSO COMPLETO!")
    print("=" * 70)
    print()
    print("Próximos passos:")
    print("1. Aguarde 1 dia para testar 'Gorgonoid Canal'")
    print("2. Aguarde 7 dias para testar 'Gorgonoid Conteúdo'")
    print("3. Use 'Análise de Views' para análises imediatas")
    print()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
