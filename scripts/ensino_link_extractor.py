import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import time
import os
import re

# ==========================================
# 1️⃣ Configurações principais
# ==========================================
SECTIONS = {
    "Cursos": {
        "Licenciaturas": "https://www.isel.pt/cursos/licenciaturas",
        "Mestrados": "https://www.isel.pt/cursos/mestrados",
        "Pós-Graduações": "https://www.isel.pt/cursos/pos-graduacoes",
        "Outros Cursos": "https://www.isel.pt/cursos/outros-cursos"
    },
    "Candidatos": {
        "Porquê o ISEL?": "https://www.isel.pt/candidatos/porque_o_ISEL",
        "Modalidades de Ingresso": "https://www.isel.pt/ensino/candidatos/modalidades-de-ingresso",
        # 🔽 Páginas internas da secção Modalidades de Ingresso (acréscimo)
        "Concurso Nacional de Acesso": "https://www.isel.pt/servicos/modalidades-de-ingresso/concurso-nacional-de-acesso",
        "Mudança de par Instituição/Curso": "https://www.isel.pt/servicos/modalidades-de-ingresso/mudanca-de-par-instituicao-curso",
        "Reingresso (Licenciatura)": "https://www.isel.pt/servicos/modalidades-de-ingresso/reingresso-licenciatura",
        "Titulares de Diploma de Especialização Tecnológica":"https://www.isel.pt/servicos/modalidades-de-ingresso/titulares-de-diploma-de-especializacao-tecnologica",
        "Titulares de Diploma de Técnico Superior Profissional":"https://www.isel.pt/servicos/modalidades-de-ingresso/titulares-de-diploma-de-tecnico-superior-profissional",
        "Maiores de 23": "https://www.isel.pt/servicos/modalidades-de-ingresso/concurso-m23",
        "Titulares de Outros Cursos Superiores": "https://www.isel.pt/servicos/modalidades-de-ingresso/titulares-de-outros-cursos-superiores",
        "Estudante Internacional": "https://www.isel.pt/servicos/modalidades-de-ingresso/estudante-internacional",
        "Mestrado (Acesso e Ingresso)": "https://www.isel.pt/servicos/modalidades-de-ingresso/mestrado",
        "Reingresso (Mestrado)": "https://www.isel.pt/servicos/modalidades-de-ingresso/reingresso-mestrado",
        "Pós-Graduação": "https://www.isel.pt/servicos/modalidades-de-ingresso/pos-graduacao",
        "Unidades Curriculares Isoladas": "https://www.isel.pt/servicos/modalidades-de-ingresso/unidades-curriculares-isoladas",
        "Unidades curriculares de ciclos de estudo subsequentes":"https://www.isel.pt/servicos/modalidades-de-ingresso/unidades-curriculares-de-ciclos-de-estudo-subsequentes",
        "Provas de Acesso": "https://www.isel.pt/ensino/candidatos/modalidades-de-ingresso/provas-de-acesso",
        "Estudante Internacional": "https://www.isel.pt/servicos/modalidades-de-ingresso/estudante-internacional"
    },
    "Programas de Mobilidade": {
        "Erasmus+ Alunos Outgoing": "https://www.isel.pt/ensino/programas-de-mobilidade/erasmus-alunos-outgoing/informacoes-gerais",
        "Erasmus+ Incoming Students": "https://www.isel.pt/ensino/programas-de-mobilidade/erasmus-alunos-incoming/informacoes-gerais",
        "Erasmus+ Staff": "https://www.isel.pt/ensino/programas-de-mobilidade/erasmus-staff/informacoes-gerais",
        "BIP – Blended Intensive Programmes": "https://www.isel.pt/ensino/programas-de-mobilidade/bip",
        "Outros Programas": "https://www.isel.pt/ensino/programas-de-mobilidade/outros-programas/informacoes-gerais/programas-de-intercambio"
    }
}

HEADERS = {"User-Agent": "Mozilla/5.0 (AI-ISEL academic crawler)"}
OUTPUT_DIR = "../data"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "ensino_links_full.xlsx")

# ==========================================
# 2️⃣ Ignorar menus globais (ajustado)
# ==========================================
def is_in_navigation(a_tag, base_path, categoria=""):
    if a_tag.find_parent(['header', 'nav', 'footer', 'aside']):
        return True
    if categoria != "Cursos":
        return False
    role = a_tag.get('role', '')
    if role and 'navigation' in role.lower():
        return True
    parent = a_tag.parent
    while parent:
        cls = " ".join(parent.get('class', []))
        if any(k in cls.lower() for k in ('menu', 'nav', 'navbar', 'header', 'footer', 'cookie', 'skip')):
            if parent.find_parent(class_="banner-curso") or \
               parent.find_parent(class_="views-field-field-menu") or \
               parent.find_parent(class_="field--name-field-menu") or \
               parent.find_parent(class_="menu--ensino"):
                return False
            return True
        parent = parent.parent
    href = a_tag.get('href', '')
    if href and (base_path in href or href.startswith("/curso/")):
        return False
    return False

# ==========================================
# 3️⃣ Extrair todos os links visíveis
# ==========================================
def extrair_links(url_base, categoria=""):
    try:
        resp = requests.get(url_base, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Erro ao aceder a {url_base}: {e}")
        return []
    DOMAIN = urlparse(url_base).netloc
    soup = BeautifulSoup(resp.text, "html.parser")
    main = (
        soup.select_one("main")
        or soup.select_one("#block-isel-content")
        or soup.select_one(".layout-content")
        or soup.select_one(".region-content")
        or soup
    )
    links = []
    vistos = set()
    for a in main.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        full_url = urljoin(url_base, href)
        parsed = urlparse(full_url)
        if parsed.netloc and parsed.netloc != DOMAIN and not full_url.lower().endswith(".pdf"):
            continue
        if is_in_navigation(a, url_base, categoria):
            continue
        text = a.get_text(strip=True) or a.get("aria-label") or a.get("title") or ""
        if not text.strip() and a.find("img"):
            img = a.find("img")
            text = img.get("alt") or img.get("title") or ""
        if not text:
            continue
        if full_url not in vistos:
            vistos.add(full_url)
            links.append((text, full_url))
    return links

# ==========================================
# 4️⃣ Extrair cursos
# ==========================================
def explorar_cursos(tipo, base_url):
    try:
        resp = requests.get(base_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Erro ao aceder à página de {tipo}: {e}")
        return []
    DOMAIN = urlparse(base_url).netloc
    soup = BeautifulSoup(resp.text, "html.parser")
    cursos = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        full_url = urljoin(base_url, href)
        if "/curso/" in full_url and DOMAIN in full_url:
            nome = a.get_text(strip=True) or a.get("title") or a.get("aria-label") or ""
            if nome:
                cursos.append((nome, full_url))
    cursos = list(dict.fromkeys(cursos))
    return cursos

# ==========================================
# 5️⃣ Loop principal
# ==========================================
all_rows = []
total_cursos = 0

visitados = set()  # 🧩 NOVO — conjunto de URLs já processadas

for categoria, subcats in SECTIONS.items():
    for subcat, url in subcats.items():
        print(f"\n🚀 A aceder à página de {subcat}: {url}\n")

        if url in visitados:  # 🧩 NOVO
            print(f"⚠️ Já visitado: {url}")
            continue
        visitados.add(url)  # 🧩 NOVO

        if categoria == "Cursos":
            cursos = explorar_cursos(subcat, url)
            print(f"🎓 Total de cursos encontrados em {subcat}: {len(cursos)}\n")
            total_cursos += len(cursos)

            for nome, link in cursos:
                if link in visitados:  # 🧩 NOVO
                    continue
                visitados.add(link)  # 🧩 NOVO

                print(f"🔍 [{subcat}] A processar: {nome}")
                links = extrair_links(link, categoria)
                print(f"   ✅ {len(links)} links recolhidos.")
                for t, u in links:
                    all_rows.append({
                        "Categoria": categoria,
                        "Subcategoria": subcat,
                        "Página": nome,
                        "Texto": t,
                        "URL": u
                    })
                time.sleep(0.5)

        else:
            print(f"🔍 [{categoria}] A processar: {subcat}")
            links = extrair_links(url, categoria)
            print(f"   ✅ {len(links)} links recolhidos.")
            for t, u in links:
                all_rows.append({
                    "Categoria": categoria,
                    "Subcategoria": subcat,
                    "Página": subcat,
                    "Texto": t,
                    "URL": u
                })

            for _, sublink in links:
                if any(x in sublink for x in [
                    "/ensino/", "/servicos/", "/programas-", "/erasmus", "/mobilidade"
                ]):
                    if sublink in visitados:  # 🧩 NOVO
                        continue
                    visitados.add(sublink)  # 🧩 NOVO

                    sublinks = extrair_links(sublink, categoria)
                    for st, su in sublinks:
                        all_rows.append({
                            "Categoria": categoria,
                            "Subcategoria": subcat,
                            "Página": sublink,
                            "Texto": st,
                            "URL": su
                        })
                    time.sleep(0.5)

# ==========================================
# 6️⃣ Gravar Excel
# ==========================================
df = pd.DataFrame(all_rows)
df.drop_duplicates(subset=["Categoria", "Subcategoria", "Página", "URL"], inplace=True)
df = df[df["URL"].str.startswith("http")]
df.sort_values(by=["Categoria", "Subcategoria", "Página", "Texto"], inplace=True)
df.to_excel(OUTPUT_FILE, index=False)

# ==========================================
# 7️⃣ Resultado final
# ==========================================
print("\n🏁 Varredura concluída!\n")
print(f"📘 Total de cursos processados: {total_cursos}")
print(f"🔗 Total de links recolhidos: {len(df)}")
print(f"📁 Guardado em: {OUTPUT_FILE}")