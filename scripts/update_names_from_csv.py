"""
Atualizar nomes dos canais usando o CSV fornecido pelo usuário
"""
import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from db import Database

def update_from_csv():
    print("=" * 70)
    print(" Atualizar Nomes dos Canais (CSV)")
    print("=" * 70)
    print()
    
    # Encontrar arquivo CSV
    csv_file = Path(__file__).parent.parent / '2026-01-04T20-13_export.csv'
    
    if not csv_file.exists():
        print("❌ Arquivo CSV não encontrado!")
        return
    
    db = Database('data/rankings.db')
    cursor = db.conn.cursor()
    
    # Ler todos os canais do banco primeiro
    cursor.execute("SELECT channel_id, title FROM channels")
    db_channels = {row['title'].lower().strip(): row['channel_id'] for row in cursor.fetchall()}
    
    print(f"📊 Canais no banco: {len(db_channels)}")
    print()
    
    # Ler CSV
    updated = 0
    not_found = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            csv_name = row['Canal'].strip()
            
            if not csv_name:
                continue
            
            # Tentar fazer match fuzzy (case-insensitive, sem espaços extras)
            csv_name_lower = csv_name.lower().strip()
            
            # Match exato
            if csv_name_lower in db_channels:
                channel_id = db_channels[csv_name_lower]
                cursor.execute("UPDATE channels SET title = ? WHERE channel_id = ?", (csv_name, channel_id))
                print(f"✅ {csv_name}")
                updated += 1
            else:
                # Tentar match parcial      
                matched = False
                for db_name, channel_id in db_channels.items():
                    if csv_name_lower in db_name or db_name in csv_name_lower:
                        cursor.execute("UPDATE channels SET title = ? WHERE channel_id = ?", (csv_name, channel_id))
                        print(f"✅ {csv_name} (matched: {db_name})")
                        updated += 1
                        matched = True
                        break
                
                if not matched:
                    not_found.append(csv_name)
    
    db.conn.commit()
    db.close()
    
    print()
    print("=" * 70)
    print(f"✅ Atualizados: {updated}")
    print(f"⚠️ Não encontrados: {len(not_found)}")
    
    if not_found:
        print()
        print("Canais não encontrados (podem não estar no banco):")
        for name in not_found[:10]:  # Mostrar primeiros 10
            print(f"  - {name}")
    
    print("=" * 70)

if __name__ == "__main__":
    update_from_csv()
