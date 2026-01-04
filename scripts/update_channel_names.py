"""
Atualizar nomes dos canais usando APENAS canais.txt (Fonte Official)
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from db import Database

def extract_handle_from_url(url):
    """Extrair @handle ou channel_id de uma URL"""
    # URLs possíveis:
    # https://www.youtube.com/@Bitelonatural
    # https://youtube.com/@renatocariani
    # @handle
    # UCxxxxxx
    
    url = url.strip()
    
    # Se já é um handle direto
    if url.startswith('@'):
        return url.lower()
    
    # Se é channel ID direto
    if url.startswith('UC') and len(url) == 24:
        return url
    
    # Extrair de URL
    match = re.search(r'@([a-zA-Z0-9_-]+)', url)
    if match:
        return '@' + match.group(1).lower()
    
    # Tentar channel ID
    match = re.search(r'(UC[a-zA-Z0-9_-]{22})', url)
    if match:
        return match.group(1)
    
    return None

def update_from_canais_txt():
    print("=" * 70)
    print(" Atualizar Nomes dos Canais (canais.txt)")
    print("=" * 70)
    print()
    
    canais_file = Path(__file__).parent.parent / 'canais.txt'
    
    if not canais_file.exists():
        print("❌ Arquivo canais.txt não encontrado!")
        return
    
    db = Database('data/rankings.db')
    cursor = db.conn.cursor()
    
    # Ler todos os canais do banco
    cursor.execute("SELECT channel_id, title, handle, custom_url FROM channels")
    db_channels = {}
    
    for row in cursor.fetchall():
        channel_id = row['channel_id']
        handle = row['handle']
        custom_url = row['custom_url']
        
        db_channels[channel_id] = {
            'id': channel_id,
            'current_title': row['title'],
            'handle': handle.lower() if handle else None,
            'custom_url': custom_url.lower() if custom_url else None
        }
    
    print(f"📊 Canais no banco: {len(db_channels)}")
    print()
    
    # Ler canais.txt
    name_mapping = {}  # Nome -> match_key (handle ou id)
    
    with open(canais_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ' - ' in line:
                parts = line.split(' - ', 1)
                custom_name = parts[0].strip()
                channel_input = parts[1].strip()
                
                handle_or_id = extract_handle_from_url(channel_input)
                if handle_or_id:
                    name_mapping[custom_name] = handle_or_id
    
    print(f"📋 Nomes customizados encontrados: {len(name_mapping)}")
    print()
    
    # Fazer matching e atualizar
    updated = 0
    not_found = []
    
    for custom_name, match_key in name_mapping.items():
        matched = False
        
        for channel_id, data in db_channels.items():
            # Match por channel ID direto
            if match_key == channel_id:
                cursor.execute("UPDATE channels SET title = ? WHERE channel_id = ?", 
                              (custom_name, channel_id))
                print(f"✅ {custom_name} (ID match)")
                updated += 1
                matched = True
                break
            
            # Match por handle
            if match_key.startswith('@') and data['handle'] and match_key == data['handle']:
                cursor.execute("UPDATE channels SET title = ? WHERE channel_id = ?", 
                              (custom_name, channel_id))
                print(f"✅ {custom_name} (handle: {match_key})")
                updated += 1
                matched = True
                break
            
            # Match por custom_url
            if data['custom_url'] and match_key in data['custom_url']:
                cursor.execute("UPDATE channels SET title = ? WHERE channel_id = ?", 
                              (custom_name, channel_id))
                print(f"✅ {custom_name} (URL match)")
                updated += 1
                matched = True
                break
        
        if not matched:
            not_found.append(f"{custom_name} ({match_key})")
    
    db.conn.commit()
    db.close()
    
    print()
    print("=" * 70)
    print(f"✅ Atualizados: {updated}/{len(name_mapping)}")
    print(f"⚠️ Não encontrados: {len(not_found)}")
    
    if not_found:
        print()
        print("Canais não encontrados no banco:")
        for name in not_found:
            print(f"  - {name}")
    
    print("=" * 70)
    print()
    print("✅ Nomes atualizados com sucesso!")
    print("Recarregue o Streamlit para ver as mudanças.")

if __name__ == "__main__":
    update_from_canais_txt()
