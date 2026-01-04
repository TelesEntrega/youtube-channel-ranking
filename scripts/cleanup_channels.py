"""
Remover canais que NÃO estão no canais.txt
Mantém apenas os canais que você definiu como oficiais
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from db import Database

def extract_handle_from_url(url):
    """Extrair @handle ou channel_id de uma URL"""
    url = url.strip()
    
    if url.startswith('@'):
        return url.lower()
    
    if url.startswith('UC') and len(url) == 24:
        return url
    
    match = re.search(r'@([a-zA-Z0-9_-]+)', url)
    if match:
        return '@' + match.group(1).lower()
    
    match = re.search(r'(UC[a-zA-Z0-9_-]{22})', url)
    if match:
        return match.group(1)
    
    return None

def cleanup_channels():
    print("=" * 70)
    print(" Limpeza de Canais - Manter APENAS canais.txt")
    print("=" * 70)
    print()
    
    canais_file = Path(__file__).parent.parent / 'canais.txt'
    
    if not canais_file.exists():
        print("❌ Arquivo canais.txt não encontrado!")
        return
    
    # Ler canais.txt e coletar todos os handles/IDs
    official_handles = set()
    official_ids = set()
    
    with open(canais_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ' - ' in line:
                parts = line.split(' - ', 1)
                channel_input = parts[1].strip()
                
                handle_or_id = extract_handle_from_url(channel_input)
                if handle_or_id:
                    if handle_or_id.startswith('@'):
                        official_handles.add(handle_or_id)
                    else:
                        official_ids.add(handle_or_id)
    
    print(f"📋 Canais oficiais (canais.txt):")
    print(f"   Handles: {len(official_handles)}")
    print(f"   IDs: {len(official_ids)}")
    print()
    
    # Conectar ao banco
    db = Database('data/rankings.db')
    cursor = db.conn.cursor()
    
    # Pegar todos os canais do banco
    cursor.execute("SELECT channel_id, title, handle FROM channels")
    all_channels = cursor.fetchall()
    
    print(f"📊 Canais no banco: {len(all_channels)}")
    print()
    
    # Identificar canais para remover
    to_remove = []
    
    for row in all_channels:
        channel_id = row['channel_id']
        title = row['title']
        handle = row['handle'].lower() if row['handle'] else None
        
        # Check se está na lista oficial
        is_official = False
        
        if channel_id in official_ids:
            is_official = True
        elif handle and handle in official_handles:
            is_official = True
        
        if not is_official:
            to_remove.append((channel_id, title))
    
    if not to_remove:
        print("✅ Nenhum canal extra encontrado. Banco já está limpo!")
        db.close()
        return
    
    print(f"⚠️ {len(to_remove)} canais serão REMOVIDOS:")
    print()
    for channel_id, title in to_remove:
        print(f"  ❌ {title}")
    print()
    
    response = input(f"Confirma remoção de {len(to_remove)} canais? (S/N): ")
    if response.upper() not in ['S', 'Y', 'SIM', 'YES']:
        print("❌ Operação cancelada")
        db.close()
        return
    
    # Remover canais
    print()
    print("Removendo...")
    
    for channel_id, title in to_remove:
        # Deletar canal (vai deletar vídeos e snapshots automaticamente por CASCADE)
        cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        print(f"  ✅ Removido: {title}")
    
    db.conn.commit()
    db.close()
    
    print()
    print("=" * 70)
    print(f"✅ {len(to_remove)} canais removidos com sucesso!")
    print(f"📊 Canais restantes: {len(all_channels) - len(to_remove)}")
    print("=" * 70)
    print()
    print("✅ Banco limpo! Apenas canais do canais.txt permanecem.")
    print("Recarregue o Streamlit para ver as mudanças.")

if __name__ == "__main__":
    cleanup_channels()
