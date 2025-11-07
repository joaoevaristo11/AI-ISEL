"""
Gera automaticamente uma lista com todos os URLs de planos de estudo
a partir do ficheiro hyperlinks.json.
"""

import json

with open("hyperlinks.json", "r", encoding="utf-8") as f:
    data = json.load(f)

planos = set()

for page in data:
    for link in page.get("links", []):
        url = link.get("url", "")
        if "/curso/" in url and "/plano-de-estudos" in url:
            planos.add(url)

planos = sorted(planos)

print(f"✅ {len(planos)} planos de estudo encontrados no site do ISEL.")

with open("planos_urls.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(planos))

print("📝 Lista guardada em planos_urls.txt")
