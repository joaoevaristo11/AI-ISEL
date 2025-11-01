import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import time

BASE_URL = "https://www.isel.pt/cursos"
DOMAIN = urlparse(BASE_URL).netloc
HEADERS = {"User-Agent": "Mozilla/5.0 (AISEL academic bot)"}

visited = set()
to_visit = [BASE_URL]
all_links = []

print("🚀 Iniciando varredura de links...\n")

while to_visit:
    url = to_visit.pop(0)
    if url in visited:
        continue
    visited.add(url)

    # ⚠️ Ignora versões em inglês
    if "/en/" in url:
        continue

    print(f"🔍 A visitar: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#"):
                continue

            full_url = urljoin(url, href)
            parsed = urlparse(full_url)

            # ⚠️ Mantém apenas links dentro do domínio e fora da versão EN
            if parsed.netloc != DOMAIN or "/en/" in parsed.path:
                continue

            # Ignora arquivos e âncoras
            if any(full_url.endswith(ext) for ext in [".pdf", ".jpg", ".png", ".zip", ".docx", ".mp4"]):
                continue

            if full_url not in visited and full_url not in to_visit:
                to_visit.append(full_url)
                all_links.append(full_url)

        time.sleep(0.5)

    except Exception as e:
        print(f"❌ Erro ao acessar {url}: {e}")

print(f"\n✅ Total de links recolhidos (sem duplicar /en): {len(all_links)}")

# ----------------------------
# 🧮 Organizar hierarquicamente
# ----------------------------

def url_to_levels(url):
    path = urlparse(url).path.strip("/")
    parts = [p for p in path.split("/") if p and p != "pt"]  # remove "pt" do caminho
    return parts

rows = []
for link in sorted(set(all_links)):
    parts = url_to_levels(link)
    row = {}
    for i, p in enumerate(parts, start=1):
        row[f"Nível {i}"] = p
    row["URL"] = link
    rows.append(row)

df = pd.DataFrame(rows)
df.to_csv("../data/isel_links_hierarquico.csv", index=False, encoding="utf-8-sig")

print(f"📁 Ficheiro gerado: ../data/isel_links_hierarquico.csv")
print(f"🧱 Total de linhas: {len(df)}")
 