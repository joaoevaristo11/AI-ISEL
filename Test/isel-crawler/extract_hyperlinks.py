# extract_hyperlinks.py
"""
Extrai todos os hyperlinks (<a href="...">) de uma lista de páginas.
Pode ler a lista do ficheiro pages_content.jsonl ou links.json.
"""

import json
import time
import argparse
from urllib.parse import urljoin
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


def main():
    parser = argparse.ArgumentParser(description="Extrair todos os hyperlinks de páginas HTML")
    parser.add_argument("--input", default="pages_content.jsonl", help="Ficheiro NDJSON com URLs")
    parser.add_argument("--out", default="hyperlinks.json", help="Ficheiro de saída")
    parser.add_argument("--delay", type=float, default=0.3, help="Atraso entre pedidos")
    parser.add_argument("--max", type=int, default=None, help="Limitar número de páginas")
    parser.add_argument("--ua", default="isel-link-extractor/1.0", help="User-Agent HTTP")
    args = parser.parse_args()

    print(f"🔍 A ler URLs de {args.input} ...")

    # Lê o ficheiro NDJSON (pages_content.jsonl)
    urls = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            urls.append(obj["url"])

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
            results.append({"page": url, "links": links})
            print(f"   ✅ {len(links)} links encontrados")
        except RequestException as e:
            print(f"   ❌ Erro: {e}")
        except Exception as e:
            print(f"   ⚠️ Erro inesperado: {e}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Hyperlinks guardados em {args.out}")


if __name__ == "__main__":
    main()
