"""
Extrai o conteúdo (título, meta, texto limpo) de uma lista de páginas guardada em links.json.
Enriquece com metadados semânticos e guarda em formato NDJSON organizado.
"""

import json
import time
import argparse
from urllib.parse import urlparse
from datetime import datetime
import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup


# ---------- utilitários ----------
def clean_dom(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove menus, scripts e elementos inúteis."""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for tag in soup.find_all(["header", "nav", "footer", "aside"]):
        tag.decompose()
    return soup


def classify_page_type(url: str) -> str:
    """Classifica a página com base no URL."""
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


def extract_content_from_html(html: str, url: str) -> dict:
    """Extrai título, meta description, H1, H2 e texto limpo."""
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"].strip()

    html_tag = soup.find("html")
    lang = (html_tag.get("lang") or "").strip().lower() if html_tag else ""

    candidates = [
        soup.select_one("main#main-content"),
        soup.select_one("main[role=main]"),
        soup.select_one("main"),
        soup.select_one("article"),
        soup.select_one("div#content"),
        soup.select_one("div.region-content"),
    ]
    container = next((c for c in candidates if c), soup.body or soup)
    h1 = (container.find("h1").get_text(" ", strip=True) if container.find("h1") else "")
    h2 = [h.get_text(" ", strip=True) for h in container.find_all("h2")[:10]]

    clean_dom(container)
    text = container.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned_lines = [ln for ln in lines if len(ln) > 2 and not ln.lower().startswith("isel - instituto")]
    text_clean = "\n".join(cleaned_lines)
    if len(text_clean) > 10000:
        text_clean = text_clean[:10000] + " …"

    domain = urlparse(url).netloc
    page_type = classify_page_type(url)

    # tenta detetar sigla
    sigla = ""
    parts = urlparse(url).path.strip("/").split("/")
    for p in parts:
        if len(p) <= 6 and p.isalpha():
            sigla = p.upper()
            break

    return {
        "url": url,
        "domain": domain,
        "type": page_type,
        "curso_sigla": sigla,
        "title": title,
        "meta_description": meta_desc,
        "h1": h1,
        "h2": h2,
        "lang": lang,
        "crawled_at": datetime.utcnow().isoformat(),
        "text": text_clean,
    }


# ---------- principal ----------
def main():
    parser = argparse.ArgumentParser(description="Extrair conteúdo de páginas guardadas em links.json (AI-ISEL)")
    parser.add_argument("--input", default="links.json", help="Ficheiro de entrada com URLs")
    parser.add_argument("--out", default="pages_content.jsonl", help="Ficheiro NDJSON de saída")
    parser.add_argument("--delay", type=float, default=0.5, help="Atraso entre pedidos (s)")
    parser.add_argument("--timeout", type=float, default=7.0, help="Timeout (s)")
    parser.add_argument("--ua", default="isel-content-extractor/2.0", help="User-Agent HTTP")
    parser.add_argument("--max", type=int, default=None, help="Limite máximo de páginas")
    args = parser.parse_args()

    print(f"🔍 A carregar URLs de {args.input} ...")
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    pages = set(data.get("pages", {}).keys())
    for links in data.get("pages", {}).values():
        for l in links:
            pages.add(l)

    pages = sorted(pages)
    if args.max:
        pages = pages[: args.max]

    print(f"✅ {len(pages)} páginas para processar.\n")

    session = requests.Session()
    session.headers.update({"User-Agent": args.ua})

    with open(args.out, "w", encoding="utf-8") as fout:
        for i, url in enumerate(pages, start=1):
            try:
                time.sleep(args.delay)
                print(f"[{i}/{len(pages)}] A extrair: {url}")
                resp = session.get(url, timeout=args.timeout)
                resp.raise_for_status()
                if "text/html" not in resp.headers.get("Content-Type", "").lower():
                    print(f"   ⚠️ Ignorado (não é HTML)")
                    continue
                content = extract_content_from_html(resp.text, url)
                fout.write(json.dumps(content, ensure_ascii=False) + "\n")
            except RequestException as e:
                print(f"   ❌ Erro ao aceder {url}: {e}")
            except Exception as e:
                print(f"   ⚠️ Erro inesperado: {e}")

    print(f"\n📝 Extração concluída! Conteúdo guardado em: {args.out}")


if __name__ == "__main__":
    main()
