import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import time
from collections import defaultdict

# ==============================
# 1️⃣ Configurações
# ==============================
BASE_URL = "https://www.isel.pt/cursos/licenciaturas"
DOMAIN = urlparse(BASE_URL).netloc
HEADERS = {"User-Agent": "Mozilla/5.0 (AI-ISEL academic crawler)"}

print(f"🚀 A aceder à página principal: {BASE_URL}\n")

# ==============================
# 2️⃣ Obter lista de licenciaturas
# ==============================
try:
    resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
except Exception as e:
    print(f"❌ Erro ao aceder à página principal: {e}")
    exit(1)

soup = BeautifulSoup(resp.text, "html.parser")

degree_links = []
for a in soup.find_all("a", href=True):
    href = a["href"].strip()
    text = a.get_text(strip=True)
    if not href or not text:
        continue

    full_url = urljoin(BASE_URL, href)
    if "/curso/licenciatura/" in full_url and DOMAIN in full_url:
        degree_links.append((text, full_url))

# Remover duplicados mantendo a ordem
degree_links = list(dict.fromkeys(degree_links))

print(f"🎓 Total de licenciaturas encontradas: {len(degree_links)}\n")

# ==============================
# 3️⃣ Função auxiliar – Ignorar menus globais
# ==============================
def is_in_navigation(a_tag, base_path):
    # Ignora links dentro de header/nav/footer/aside ou com role="navigation"
    if a_tag.find_parent(['header', 'nav', 'footer', 'aside']):
        return True
    role = a_tag.get('role', '')
    if role and 'navigation' in role.lower():
        return True

    # classes comuns de menus/rodapés
    parent = a_tag.parent
    while parent:
        cls = " ".join(parent.get('class', []))
        if any(k in cls.lower() for k in ('menu', 'nav', 'navbar', 'header', 'footer', 'cookie', 'skip')):
            return True
        parent = parent.parent

    # ⚠️ exceção: se for um link interno de curso (/curso/...), não ignorar
    href = a_tag.get('href', '')
    if href and href.startswith("/curso/"):
        # permitir se for subpágina do mesmo curso (ex: plano de estudos)
        if base_path in href:
            return False

    return False

# ==============================
# 4️⃣ Varredura de cada licenciatura
# ==============================
all_rows = []
pdf_links = set()
links_por_lic = defaultdict(set)

for degree_name, degree_url in degree_links:
    print(f"🔍 A processar: {degree_name}")

    try:
        resp = requests.get(degree_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Erro ao aceder a {degree_url}: {e}")
        continue

    soup = BeautifulSoup(resp.text, "html.parser")

    # 🔸 Apenas o conteúdo principal (ignora menus globais automaticamente)
    main_content = (
        soup.select_one("main")
        or soup.select_one(".layout-content")
        or soup.select_one(".region-content")
        or soup
    )

    for a in main_content.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue

        full_url = urljoin(degree_url, href)
        parsed = urlparse(full_url)

        # Ignorar links externos (exceto PDFs)
        if parsed.netloc and parsed.netloc != DOMAIN and not full_url.lower().endswith(".pdf"):
            continue

        # Ignorar links de navegação global
        if (not text.strip() and a.find('img')) or is_in_navigation(a, degree_url):
            continue

        # Texto visível ou de fallback
        text = a.get_text(strip=True) or a.get('aria-label') or a.get('title') or ""

        # Ignorar links vazios
        if not text.strip() and a.find('img'):
            continue

        # Identificar PDFs
        if full_url.lower().endswith(".pdf"):
            pdf_links.add(full_url)

        links_por_lic[degree_name].add((text or "(sem texto visível)", full_url))

    print(f"   ✅ {len(links_por_lic[degree_name])} links únicos recolhidos.\n")
    time.sleep(0.5)

# ==============================
# 5️⃣ Identificar links comuns
# ==============================
link_count = defaultdict(int)
for lic, links in links_por_lic.items():
    for _, url in links:
        link_count[url] += 1

for lic, links in links_por_lic.items():
    for text, url in links:
        lic_name = "Licenciaturas Comum" if link_count[url] > 1 else lic
        all_rows.append({
            "Licenciatura": lic_name,
            "Texto": text,
            "URL": url
        })

# ==============================
# 6️⃣ Limpeza e gravação
# ==============================
df = pd.DataFrame(all_rows).drop_duplicates(subset=["Licenciatura", "URL"])
df = df[df["URL"].str.startswith("http")]
df.sort_values(by=["Licenciatura", "Texto"], inplace=True)

output_excel = "../data/licenciaturas_links_full.xlsx"
df.to_excel(output_excel, index=False)

# ==============================
# 7️⃣ Output final
# ==============================
print("🏁 Varredura concluída!\n")
print(f"🎓 Total de licenciaturas processadas: {len(degree_links)}")
print(f"🔗 Total de links únicos: {len(df)}")
print(f"📄 Total de PDFs encontrados: {len(pdf_links)}")
print(f"📁 Guardado em: {output_excel}")
