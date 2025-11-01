import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import fitz  # PyMuPDF
import io


# === 1️⃣ LER O CSV CORRETAMENTE ===
csv_path = "../data/pages2.csv"

# Detectar automaticamente a linha onde começa o cabeçalho
with open(csv_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Encontrar a primeira linha que contenha "Secção"
header_line = next(i for i, line in enumerate(lines) if "Secção" in line)

# Ler o CSV a partir dessa linha
df = pd.read_csv(csv_path, sep=";", header=header_line)
df = df.fillna(method="ffill")

# Lista para guardar as páginas extraídas
pages = []

headers = {"User-Agent": "Mozilla/5.0 (AISEL academic bot)"}


def limpar_texto(texto):
    """Remove espaços e quebras desnecessárias"""
    return " ".join(texto.split())


# === 2️⃣ LER AS PÁGINAS HTML ===
for i, row in df.iterrows():
    secao = str(row.get("Secção", ""))
    subsecao = str(row.get("Subsecção", ""))
    url = str(row.get("URL completo", ""))
    titulo = str(row.get("Título", ""))

    # Ignora URLs vazios ou inválidos
    if not url or not url.startswith("http"):
        print(f"⚠️ URL inválido (linha {i}): '{url}'")
        continue

    # Ignora PDFs (tratamos depois)
    if "pdf" in url.lower():
        continue

    print(f"📖 [{secao or '?'} > {subsecao or '?'}] A ler: {url}")

    try:
        resposta = requests.get(url, headers=headers, timeout=20)
        if resposta.status_code != 200:
            print(f"⚠️ Erro {resposta.status_code} ao abrir {url}")
            continue

        soup = BeautifulSoup(resposta.text, "html.parser")

        # Extrai o conteúdo principal (<main>) ou todo o HTML
        main = soup.select_one("main") or soup

        # Extrai parágrafos
        paragrafos = [p.get_text(" ", strip=True) for p in main.find_all("p")]
        texto = limpar_texto(" ".join(paragrafos))

        # Caso o texto seja curto, adiciona headings
        if len(texto) < 150:
            heads = [h.get_text(" ", strip=True) for h in soup.select("h1,h2,h3")]
            texto = limpar_texto(" ".join(heads + paragrafos))

        pages.append({
            "secção": secao,
            "subsecção": subsecao,
            "url": url,
            "titulo": titulo,
            "conteudo": texto
        })

        print(f"✅ Extraído: {len(texto)} caracteres")
        time.sleep(1)

    except Exception as e:
        print(f"❌ Erro a processar {url}: {e}")

# === 4️⃣ GUARDAR O RESULTADO EM JSON ===
output_path = "../data/pages.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(pages, f, ensure_ascii=False, indent=2)

print("\n🎉 Ficheiro pages.json criado com sucesso!")
print(f"Total de páginas extraídas: {len(pages)}")
