import json
import time
<<<<<<< Updated upstream
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
=======
>>>>>>> Stashed changes

HEADERS = {"User-Agent": "Mozilla/5.0 (AISEL academic bot)"}
INPUT_XLSX = "../data/isel_site_tree.xlsx"
INPUT_CSV = "../data/isel_links_hierarquico.csv"
OUTPUT_JSON = "../data/isel_site_tree_pages.json"

# padrões de subpáginas que queremos capturar (fragmento do href -> rótulo)
SUBPAGE_PATTERNS = {
    "plano-de-estudos": "Plano de Estudos",
    "ementa": "Ementa",
    "programa": "Programa",
    "horario": "Horário",
    "contactos": "Contactos",
    "horário": "Horário"  # variação com acento
}

TIMEOUT = 8
SLEEP_BETWEEN = 0.25

def load_input():
    # tenta primeiro o Excel, depois o CSV
    if os.path.exists(INPUT_XLSX):
        df = pd.read_excel(INPUT_XLSX, engine="openpyxl", dtype=str).fillna("")
    elif os.path.exists(INPUT_CSV):
        df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
    else:
        raise FileNotFoundError(f"Nem {INPUT_XLSX} nem {INPUT_CSV} encontrados.")
    return df

def find_url_column(df):
    # retorna o nome da coluna que contém 'url' (case-insensitive)
    for col in df.columns:
        if "url" in col.lower():
            return col
    # fallback: se existir coluna exatamente "URL"
    if "URL" in df.columns:
        return "URL"
    raise KeyError("Coluna com URL não encontrada no ficheiro de entrada.")

def extract_subpages_from_html(page_url, soup):
    found = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
# === 1️⃣ LER O NOVO CSV ===
csv_path = "../data/isel_site_tree.csv"

df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
df = df.fillna("")  # substituir NaN por vazio

print(f"✅ CSV lido com sucesso ({len(df)} linhas)")
print("Colunas:", df.columns.tolist())

# === 2️⃣ LISTA PARA GUARDAR OS RESULTADOS ===
pages = []

headers = {"User-Agent": "Mozilla/5.0 (AISEL academic bot)"}


def limpar_texto(texto):
    """Remove espaços e quebras desnecessárias"""
    return " ".join(texto.split())


# === 3️⃣ LER AS PÁGINAS HTML ===
for i, row in df.iterrows():
    url = str(row.get("URL", "")).strip()

    # Ignorar linhas sem URL ou inválidas
    if not url or not url.startswith("http"):
        print(f"⚠️ URL inválido (linha {i}): '{url}'")
        continue

    # Ignorar PDFs
    if "pdf" in url.lower():
        continue

    grupo = row.get("Grupo", "")
    subgrupo = row.get("Subgrupo", "")
    subsub = row.get("Sub-subgrupo", "")
    subsubsub = row.get("Sub-sub-subgrupo", "")
    subsubsubsub = row.get("Sub-sub-sub-subgrupo", "")
    nivel6 = row.get("Nível 6", "")
    nivel7 = row.get("Nível 7", "")
    nivel8 = row.get("Nível 8", "")
    nivel9 = row.get("Nível 9", "")

    print(f"📖 [{grupo} > {subgrupo} > {subsub}] A ler: {url}")

    try:
        resposta = requests.get(url, headers=headers, timeout=20)
        if resposta.status_code != 200:
            print(f"⚠️ Erro {resposta.status_code} ao abrir {url}")
            continue
        # cria full url
        full = href if href.startswith("http") else urljoin(page_url, href)
        lower = full.lower()
        for pattern, label in SUBPAGE_PATTERNS.items():
            if pattern in lower:
                if label not in found:
                    found[label] = {"title": a.get_text(strip=True) or label, "url": full}
    return found

<<<<<<< Updated upstream
def build_json_records(df):
    url_col = find_url_column(df)
    level_cols = [c for c in df.columns if c != url_col]
    records = []
    seen_urls = set()

    for _, row in df.iterrows():
        page_url = (row.get(url_col) or "").strip()
        if not page_url or page_url in seen_urls:
            continue
        seen_urls.add(page_url)

        levels = {col: (row.get(col) or "") for col in level_cols}
        rec = {"levels": levels, "url": page_url, "subpages": {}}

        # fetch page and probe for subpages
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 200 and "text/html" in resp.headers.get("Content-Type", ""):
                soup = BeautifulSoup(resp.text, "html.parser")
                subpages = extract_subpages_from_html(page_url, soup)
                rec["subpages"] = subpages
            else:
                rec["subpages"] = {}
        except Exception as e:
            rec["error"] = str(e)

        records.append(rec)
        print(f"✔ Processado: {page_url} (subpáginas: {len(rec['subpages'])})")
        time.sleep(SLEEP_BETWEEN)
    return records
=======
        soup = BeautifulSoup(resposta.text, "html.parser")
        main = soup.select_one("main") or soup

        # Extrai texto de parágrafos
        paragrafos = [p.get_text(" ", strip=True) for p in main.find_all("p")]
        texto = limpar_texto(" ".join(paragrafos))

        # Adiciona headings se o texto for curto
        if len(texto) < 150:
            heads = [h.get_text(" ", strip=True) for h in soup.select("h1,h2,h3")]
            texto = limpar_texto(" ".join(heads + paragrafos))

        pages.append({
            "url": url,
            "grupo": grupo,
            "subgrupo": subgrupo,
            "subsub": subsub,
            "subsubsub": subsubsub,
            "subsubsubsub": subsubsubsub,
            "nivel6": nivel6,
            "nivel7": nivel7,
            "nivel8": nivel8,
            "nivel9": nivel9,
            "conteudo": texto
        })
>>>>>>> Stashed changes

def main():
    df = load_input()
    records = build_json_records(df)
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON gravado em: {OUTPUT_JSON} — total entradas: {len(records)}")

<<<<<<< Updated upstream
if __name__ == "__main__":
    main()
=======
    except Exception as e:
        print(f"❌ Erro a processar {url}: {e}")

# === 4️⃣ GUARDAR EM JSON ===
output_path = "../data/pages.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(pages, f, ensure_ascii=False, indent=2)

print("\n🎉 Ficheiro pages.json criado com sucesso!")
print(f"Total de páginas extraídas: {len(pages)}")
>>>>>>> Stashed changes