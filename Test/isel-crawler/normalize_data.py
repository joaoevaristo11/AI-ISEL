"""
🔹 Normaliza e unifica todos os ficheiros de extração do site do ISEL
(links.json, pages_content.jsonl, hyperlinks.json, planos_estudo_fuc_completo.json)
num único dataset completo: dataset_isel_completo.json (+ opcional CSV)
"""

import json
import csv
import argparse
from pathlib import Path


# ========== UTILITÁRIOS ==========

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Ficheiro não encontrado: {path}")
        return []
    except Exception as e:
        print(f"⚠️ Erro a ler {path}: {e}")
        return []


def load_jsonl(path):
    data = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    except FileNotFoundError:
        print(f"⚠️ Ficheiro não encontrado: {path}")
    return data


def normalize_url(url: str):
    if not url:
        return ""
    url = url.strip().replace("http://", "https://")
    if "#" in url:
        url = url.split("#")[0]
    if url.endswith("/"):
        url = url[:-1]
    return url


def clean_and_enrich_links(links):
    """Remove duplicados e melhora textos vazios nos links."""
    cleaned = []
    seen = set()

    for l in links:
        url = l.get("url", "").strip()
        text = l.get("text", "").strip()
        if not url or url in seen:
            continue
        seen.add(url)

        if not text:
            last_seg = url.rstrip("/").split("/")[-1]
            text = last_seg.replace("-", " ").capitalize() if last_seg else "Link"

        cleaned.append({"text": text, "url": url})

    return cleaned


# ========== MAIN ==========

def main():
    parser = argparse.ArgumentParser(description="Unificar dados extraídos do site do ISEL")
    parser.add_argument("--csv", action="store_true", help="Exportar também para CSV (dataset_isel_completo.csv)")
    args = parser.parse_args()

    base_dir = Path(".")
    output_json = base_dir / "dataset_isel_completo.json"
    output_csv = base_dir / "dataset_isel_completo.csv"

    print("📦 A carregar ficheiros...\n")

    links_data = load_json(base_dir / "links.json")
    pages_data = load_jsonl(base_dir / "pages_content.jsonl")
    hyperlinks_data = load_json(base_dir / "hyperlinks.json")
    planos_data = load_json(base_dir / "planos_estudo_fuc_completo.json")

    dataset = {}

    # === 1. Páginas com conteúdo extraído ===
    for page in pages_data:
        url = normalize_url(page.get("url"))
        dataset.setdefault(url, {})
        dataset[url]["titulo"] = page.get("title", "")
        dataset[url]["texto"] = page.get("text", "")
        dataset[url]["h1"] = page.get("h1", "")
        dataset[url]["h2"] = page.get("h2", [])
        dataset[url]["meta_description"] = page.get("meta_description", "")
        dataset[url]["lang"] = page.get("lang", "")

    # === 2. Links extraídos ===
    for item in hyperlinks_data:
        page = normalize_url(item.get("page"))
        dataset.setdefault(page, {})
        existing = dataset[page].get("links", [])
        dataset[page]["links"] = clean_and_enrich_links(existing + item.get("links", []))

    # === 3. Planos de Estudo + FUCs ===
    for plano in planos_data:
        url = normalize_url(plano.get("url"))
        dataset.setdefault(url, {})
        dataset[url]["curso"] = plano.get("curso", "")
        dataset[url]["tabelas"] = plano.get("tabelas", [])

        fucs = []
        for tab in plano.get("tabelas", []):
            for row in tab.get("rows", []):
                if "FUC_PDF" in row:
                    fucs.append({
                        "pdf": row["FUC_PDF"],
                        "texto": row.get("FUC_TEXT", "")
                    })
        if fucs:
            dataset[url]["fucs"] = fucs

    # === 4. Links globais do crawler (links.json) ===
    if isinstance(links_data, dict) and "pages" in links_data:
        for page, out_links in links_data["pages"].items():
            page_norm = normalize_url(page)
            dataset.setdefault(page_norm, {})
            links = [{"text": "", "url": normalize_url(l)} for l in out_links]
            dataset[page_norm]["links"] = clean_and_enrich_links(dataset[page_norm].get("links", []) + links)

    # === 5. Limpeza e normalização final ===
    print("\n🧹 A normalizar e remover duplicados...")
    for url, data in dataset.items():
        if "links" in data:
            data["links"] = clean_and_enrich_links(data["links"])

    # === 6. Guardar JSON final ===
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Dataset final guardado em: {output_json.resolve()}")
    print(f"📊 Total de páginas integradas: {len(dataset)}")

    # === 7. (Opcional) Exportar CSV simples ===
    if args.csv:
        print("🧾 A gerar CSV...")
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["URL", "Título", "Descrição", "Texto", "Idioma", "Nº de links", "Nº de FUCs"])
            for url, data in dataset.items():
                w.writerow([
                    url,
                    data.get("titulo", ""),
                    data.get("meta_description", ""),
                    (data.get("texto", "")[:150] + "...") if len(data.get("texto", "")) > 150 else data.get("texto", ""),
                    data.get("lang", ""),
                    len(data.get("links", [])),
                    len(data.get("fucs", [])) if "fucs" in data else 0
                ])
        print(f"✅ CSV exportado para: {output_csv.resolve()}")


if __name__ == "__main__":
    main()
