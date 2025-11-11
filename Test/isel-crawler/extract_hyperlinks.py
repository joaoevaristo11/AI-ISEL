# extract_hyperlinks.py (versão otimizada AI-ISEL)
"""
Extrai todos os hyperlinks (<a href="...">) de uma lista de páginas HTML.
Pode ler a lista do ficheiro pages_content.jsonl ou links.json.
Adiciona metadados úteis (type, domain, count) para o dataset.
"""

import json
import time
import argparse
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException


def extract_links_from_html(html: str, base_url: str):
    """Extrai todos os links absolutos de uma página HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)
        full_url = urljoin(base_url, href)
        links.append({"text": text, "url": full_url})
    return links


def classify_page_type(url: str) -> str:
    """Classifica página com base no URL."""
    u = url.lower()
    if "/curso/" in u and "/plano-de-estudos" in u:
        return "plano_estudos"
    elif "/curso/" in u:
        return "curso"
    elif "/noticias/" in u or "/news/" in u:
        return "noticia"
    elif "/candidatos/" in u or "propinas" in u or "calendario" in u:
        return "admissao"
    elif "/servicos/" in u or "/comunidade/" in u:
        return "servico"
    elif "/o-isel" in u or "/about" in u:
        return "institucional"
    else:
        return "outro"


def main():
    parser = argparse.ArgumentParser(description="Extrair todos os hyperlinks de páginas HTML (AI-ISEL)")
    parser.add_argument("--input", default="pages_content.jsonl", help="Ficheiro NDJSON com URLs")
    parser.add_argument("--out", default="hyperlinks.json", help="Ficheiro de saída JSON")
    parser.add_argument("--delay", type=float, default=0.3, help="Atraso entre pedidos (segundos)")
    parser.add_argument("--max", type=int, default=None, help="Limitar número de páginas")
    parser.add_argument("--ua", default="isel-link-extractor/2.0", help="User-Agent HTTP")
    args = parser.parse_args()

    print(f"🔍 A ler URLs de {args.input} ...")

    urls = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            urls.append(obj.get("url"))

    if args.max:
        urls = urls[:args.max]

    print(f"✅ {len(urls)} páginas para processar.\n")

    session = requests.Session()
    session.headers.update({"User-Agent": args.ua})

    results = []

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] A extrair links de: {url}")
        try:
            time.sleep(args.delay)
            resp = session.get(url, timeout=8)
            resp.raise_for_status()
            if "text/html" not in resp.headers.get("Content-Type", ""):
                continue

            links = extract_links_from_html(resp.text, url)
            page_type = classify_page_type(url)
            results.append({
                "page": url,
                "type": page_type,
                "domain": urlparse(url).netloc,
                "total_links": len(links),
                "links": links
            })
            print(f"   ✅ {len(links)} links encontrados ({page_type})")

        except RequestException as e:
            print(f"   ❌ Erro HTTP: {e}")
        except Exception as e:
            print(f"   ⚠️ Erro inesperado: {e}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Hyperlinks guardados em {args.out}")


if __name__ == "__main__":
    main()
