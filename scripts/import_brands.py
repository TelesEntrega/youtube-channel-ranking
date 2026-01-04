"""
Importar marcas do marcas.txt com matching inteligente
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from db import Database

def normalize_name(name):
    """Normalize name for comparison"""
    return name.lower().strip().replace('  ', ' ')

def import_brands():
    print("=" * 70)
    print(" Importação de Marcas/Patrocínios (Matching Inteligente)")
    print("=" * 70)
    print()
    
    marcas_file = Path(__file__).parent.parent / 'marcas.txt'
    if not marcas_file.exists():
        print("❌ ERRO: Arquivo 'marcas.txt' não encontrado!")
        return
    
    db = Database('data/rankings.db')
    cursor = db.conn.cursor()
    
    # Get all channels from database
    cursor.execute("SELECT channel_id, title FROM channels")
    db_channels = {normalize_name(row['title']): row['title'] for row in cursor.fetchall()}
    
    print(f"📊 Canais no banco: {len(db_channels)}")
    print(f"📄 Lendo arquivo: {marcas_file}")
    print()
    
    updated = 0
    not_found = []
    
    with open(marcas_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '|' in line:
                parts = line.split('|', 1)
                channel_name = parts[0].strip()
                brand = parts[1].strip()
                
                if not brand or brand == '?':
                    continue
                
                # Try to find match
                normalized = normalize_name(channel_name)
                
                if normalized in db_channels:
                    actual_title = db_channels[normalized]
                    cursor.execute("UPDATE channels SET brand = ? WHERE title = ?", 
                                  (brand, actual_title))
                    db.conn.commit()
                    print(f"  ✅ {channel_name} → {brand}")
                    updated += 1
                else:
                    not_found.append(channel_name)
    
    db.close()
    
    print()
    print("=" * 70)
    print(f"✅ Atualizadas: {updated} marcas")
    print(f"⚠️ Não encontrados: {len(not_found)}")
    
    if not_found:
        print()
        print("Canais não encontrados:")
        for name in not_found:
            print(f"  - {name}")
    
    print("=" * 70)
    print()
    print("✅ Importação concluída!")
    print("Recarregue o Streamlit para ver as marcas.")

if __name__ == "__main__":
    import_brands()
