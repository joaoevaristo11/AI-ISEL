import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import fitz  # PyMuPDF
import io


# === 1️⃣ LER O CSV ===
df = pd.read_csv("../data/pages.csv", sep=";")

# Lista para guardar as páginas extraídas
pages = []

headers = {"User-Agent": "Mozilla/5.0 (AISEL academic bot)"}


def limpar_texto(texto):
    """Remove espaços e quebras desnecessárias"""
    return " ".join(texto.split())


# === 2️⃣ LER AS PÁGINAS HTML ===
for i, row in df.iterrows():
    categoria = str(row["Categoria"])
    url = str(row["URL completo"])
    titulo = str(row["Título"])

    # Ignora PDFs (tratamos depois)
    if "pdf" in url.lower():
        continue

    print(f"📖 A ler: {url}")

    try:
        resposta = requests.get(url, headers=headers, timeout=20)
        if resposta.status_code != 200:
            print(f"⚠️ Erro {resposta.status_code} ao abrir {url}")
            continue

        soup = BeautifulSoup(resposta.text, "html.parser")

        # Extrai o conteúdo principal (<main>) ou todo o HTML
        main = soup.select_one("main") or soup
        paragrafos = [p.get_text(" ", strip=True) for p in main.find_all("p")]
        texto = limpar_texto(" ".join(paragrafos))

        # Caso o texto seja curto, adiciona headings
        if len(texto) < 150:
            heads = [h.get_text(" ", strip=True) for h in soup.select("h1,h2,h3")]
            texto = limpar_texto(" ".join(heads + paragrafos))

        pages.append({
            "categoria": categoria,
            "url": url,
            "titulo": titulo,
            "conteudo": texto
        })

        print(f"✅ Extraído: {len(texto)} caracteres")
        time.sleep(1)

    except Exception as e:
        print(f"❌ Erro a processar {url}: {e}")


# === 3️⃣ LER PDFs (como a brochura dos cursos) ===
pdf_rows = df[df["Caminho"].str.contains("ficheiro PDF", case=False, na=False)]

for i, row in pdf_rows.iterrows():
    pdf_url = str(row["URL completo"])
    titulo = str(row["Título"])
    categoria = str(row["Categoria"])

    print(f"📄 A extrair texto do PDF: {pdf_url}")

    try:
        res = requests.get(pdf_url, headers=headers, timeout=30)
        res.raise_for_status()
        pdf_bytes = io.BytesIO(res.content)

        # Abre o PDF com fitz (PyMuPDF)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texto_total = ""
        for pagina in doc:
            texto_total += pagina.get_text("text") + "\n"

        doc.close()

        pages.append({
            "categoria": categoria,
            "url": pdf_url,
            "titulo": titulo,
            "conteudo": limpar_texto(texto_total)
        })

        print(f"✅ PDF extraído com sucesso ({len(texto_total)} caracteres)")

    except Exception as e:
        print(f"❌ Erro a processar PDF {pdf_url}: {e}")


# === 4️⃣ GUARDAR O RESULTADO EM JSON ===
with open("../data/pages.json", "w", encoding="utf-8") as f:
    json.dump(pages, f, ensure_ascii=False, indent=2)

print("\n🎉 Ficheiro pages.json criado com sucesso!")
print(f"Total de páginas extraídas: {len(pages)}")
