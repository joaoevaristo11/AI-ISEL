"""
Gera automaticamente uma lista com todos os URLs de planos de estudo
a partir do ficheiro hyperlinks.json, com metadados organizados.
"""

import json
from urllib.parse import urlparse

def main():
    with open("hyperlinks.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    planos = []

    for page in data:
        page_url = page.get("page", "")
        domain = urlparse(page_url).netloc
        for link in page.get("links", []):
            url = link.get("url", "")
            text = link.get("text", "")
            if "/curso/" in url and "/plano-de-estudos" in url:
                sigla = None
                path_parts = urlparse(url).path.strip("/").split("/")
                for p in path_parts:
                    if len(p) <= 6 and p.isalpha():
                        sigla = p.upper()
                        break
                planos.append({
                    "url": url,
                    "text": text,
                    "curso_sigla": sigla or "",
                    "domain": domain,
                    "type": "plano_estudos"
                })

    print(f"✅ {len(planos)} planos de estudo encontrados no site do ISEL.")

    with open("planos_urls.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(p["url"] for p in planos)))

    with open("planos_urls_detalhados.json", "w", encoding="utf-8") as f:
        json.dump(planos, f, ensure_ascii=False, indent=2)

    print("📝 Lista guardada em planos_urls.txt e planos_urls_detalhados.json")

if __name__ == "__main__":
    main()
