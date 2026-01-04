"""
Script to create placeholder logos for brands found in marcas.txt
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

def create_brand_logos():
    marcas_file = Path(r'c:\Users\Rankine\Documents\Ranking Gorgonoid\marcas.txt')
    logos_dir = Path(r'c:\Users\Rankine\Documents\Ranking Gorgonoid\assets\logos')
    
    if not logos_dir.exists():
        os.makedirs(logos_dir)
        
    # Get unique brands
    brands = set()
    with open(marcas_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '|' in line and not line.startswith('#'):
                brand = line.split('|')[1].strip()
                if brand and brand not in ['?', 'Sem Patrocínio']:
                    brands.add(brand)
    
    print(f"Marcas encontradas: {len(brands)}")
    
    # Create logos
    for brand in brands:
        # Create safe filename
        safe_name = brand.lower().replace(' ', '_').replace('.', '')
        filename = logos_dir / f"{safe_name}.png"
        
        # Don't overwrite existing
        if filename.exists():
            print(f"Logo existe: {filename.name}")
            continue
            
        print(f"Criando placeholder: {filename.name}")
        
        # Create image
        width, height = 100, 100
        color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
        img = Image.new('RGB', (width, height), color=color)
        d = ImageDraw.Draw(img)
        
        # Text based (would need font, just simple rectangle for now)
        d.rectangle([10, 40, 90, 60], fill=(255, 255, 255))
        
        img.save(filename)

if __name__ == "__main__":
    try:
        create_brand_logos()
        print("Sucesso! Logos criados em assets/logos")
    except Exception as e:
        print(f"Erro: {e}")
