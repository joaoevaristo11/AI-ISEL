import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd

# ==============================
# 1️⃣ Configurações
# ==============================
BASE_URL = "https://www.isel.pt/curso/licenciatura/licenciatura-em-engenharia-informatica-redes-e-telecomunicacoes"
DOMAIN = urlparse(BASE_URL).netloc
HEADERS = {"User-Agent": "Mozilla/5.0 (AI-ISEL academic crawler)"}

print(f"🚀 A aceder à página: {BASE_URL}\n")

# ==============================
# 2️⃣ Requisição e parsing
# ==============================
try:
    resp = requests.get(BASE_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
except Exception as e:
    print(f"❌ Erro ao aceder à página principal: {e}")
    exit(1)

soup = BeautifulSoup(resp.text, "html.parser")

# ==============================
# 3️⃣ Extração de links
# ==============================
links = []
pdf_links = []

for a in soup.find_all("a", href=True):
    href = a["href"].strip()
    if not href or href.startswith("#"):
        continue

    full_url = urljoin(BASE_URL, href)
    parsed = urlparse(full_url)

    # Ignora links externos (exceto PDFs)
    if parsed.netloc and parsed.netloc != DOMAIN and not full_url.lower().endswith(".pdf"):
        continue

    # Identifica se é PDF
    if full_url.lower().endswith(".pdf"):
        pdf_links.append(full_url)

    text = a.get_text(strip=True)
    links.append({
        "Texto": text if text else "(sem texto visível)",
        "URL": full_url
    })

# ==============================
# 4️⃣ Limpeza e gravação
# ==============================
df = pd.DataFrame(links).drop_duplicates(subset=["URL"])
df = df[df["URL"].str.startswith("http")]  # mantém apenas URLs válidos

output_csv = "../data/leirt_links_full.csv"
df.to_csv(output_csv, index=False, encoding="utf-8-sig")

# ==============================
# 5️⃣ Output limpo no terminal
# ==============================
total_links = len(df)
total_pdfs = len(set(pdf_links))

print(f"✅ {total_links} links internos encontrados.\n")
print(f"📄 Total de PDFs encontrados: {total_pdfs}")
print(f"📁 Guardado em: {output_csv}")
