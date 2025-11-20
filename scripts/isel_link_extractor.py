import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import time
import os
import re

from sections import SECTIONS

HEADERS = {"User-Agent": "Mozilla/5.0 (AI-ISEL academic crawler)"}
OUTPUT_DIR = "../data"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "isel_links_full.xlsx")

CATEGORIAS_COM_CURSOS = {"Cursos"}
CATEGORIAS_QUEM_SOMOS = {"Quem Somos"}

# ---------------- Normalização de URL ----------------
def normalizar_url(u: str) -> str:
    if not u:
        return ""
    # remover fragmentos e espaços
    u = u.strip()
    if "#" in u:
        u = u.split("#", 1)[0]
    # remover barra final (exceto raiz)
    if len(u) > 1 and u.endswith("/"):
        u = u[:-1]
    return u

# ---------------- Links em atributos/JS ----------------
ATTR_PATTERN = re.compile(r"(https?://[^\s'\"<>]+|/[^\s'\"<>]+)")
def extrair_links_de_atributos(root, base_url, domain):
    encontrados = []
    for el in root.find_all(True):
        for attr in ("data-href", "data-url", "data-link", "onclick"):
            val = el.get(attr)
            if not val:
                continue
            # onclick pode conter window.location='...'
            if attr == "onclick":
                candidatos = ATTR_PATTERN.findall(val)
            else:
                candidatos = [val]
            for c in candidatos:
                full = urljoin(base_url, c)
                p = urlparse(full)
                if p.netloc and p.netloc != domain and not full.lower().endswith(".pdf"):
                    continue
                txt = el.get_text(strip=True) or el.get("aria-label") or el.get("title") or c
                encontrados.append((txt, normalizar_url(full)))
    # deduplicar mantendo ordem
    vistos_local = set()
    res = []
    for t, u in encontrados:
        if u not in vistos_local:
            vistos_local.add(u)
            res.append((t, u))
    return res

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
    # atributos extras
    extras = extrair_links_de_atributos(main, url_base, DOMAIN)
    for t, u in extras:
        if u not in vistos:
            vistos.add(u)
            links.append((t, u))
    for a in main.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        full_url = normalizar_url(urljoin(url_base, href))
        parsed = urlparse(full_url)
        if parsed.netloc and parsed.netloc != DOMAIN and not full_url.lower().endswith(".pdf"):
            continue
        if is_in_navigation(a, url_base, categoria):
            continue
        text = a.get_text(strip=True) or a.get("aria-label") or a.get("title") or ""
        if not text and a.find("img"):
            img = a.find("img")
            text = img.get("alt") or img.get("title") or ""
        if not text:
            continue
        if full_url not in vistos:
            vistos.add(full_url)
            links.append((text, full_url))
    return links

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
        full_url = normalizar_url(urljoin(base_url, href))
        if ("/curso/" in full_url or "/ensino/cursos/outros-cursos/" in full_url) and DOMAIN in full_url:
            nome = a.get_text(strip=True) or a.get("title") or a.get("aria-label") or ""
            if nome:
                cursos.append((nome, full_url))
    cursos = list(dict.fromkeys(cursos))
    return cursos

def explorar_quem_somos(tipo, base_url):
    try:
        resp = requests.get(base_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Erro ao aceder à página de {tipo}: {e}")
        return []
    DOMAIN = urlparse(base_url).netloc
    soup = BeautifulSoup(resp.text, "html.parser")
    encontrados = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = normalizar_url(urljoin(base_url, href))
        if ("/departamento/" in full_url or "/servicos/" in full_url) and DOMAIN in full_url:
            nome = a.get_text(strip=True) or a.get("title") or a.get("aria-label") or ""
            if nome:
                encontrados.append((nome, full_url))
    encontrados = list(dict.fromkeys(encontrados))
    return encontrados

# ---------------- Loop principal ----------------
all_rows = []
visitados_profundo = set()   # URLs já seguidos em profundidade
total_cursos = 0

for categoria, subcats in SECTIONS.items():
    print(f"\n==============================")
    print(f"📌 Categoria: {categoria}")
    print("==============================\n")
    for subcat, url in subcats.items():
        url_norm = normalizar_url(url)
        print(f"\n🚀 A aceder à página de {subcat}: {url_norm}\n")

        # Não bloquear reaproveitamento do mesmo URL entre categorias/subcats
        print(f"🔍 [{categoria}] A processar: {subcat}")

        # Cursos
        if categoria in CATEGORIAS_COM_CURSOS:
            cursos = explorar_cursos(subcat, url_norm)
            print(f"🎓 Total de cursos encontrados: {len(cursos)}\n")
            total_cursos += len(cursos)
            for nome, link in cursos:
                link_norm = normalizar_url(link)
                links_extra = extrair_links(link_norm, categoria)
                # registar todos os links dessa página de curso
                for t, u in links_extra:
                    all_rows.append({
                        "Categoria": categoria,
                        "Subcategoria": subcat,
                        "Página": nome,
                        "Texto": t,
                        "URL": u
                    })
                # seguir profundidade (apenas uma vez por URL global)
                if link_norm not in visitados_profundo:
                    visitados_profundo.add(link_norm)
        # Quem Somos subpáginas
        elif categoria in CATEGORIAS_QUEM_SOMOS and subcat in {"Departamentos", "Serviços", "Órgãos"}:
            subpaginas = explorar_quem_somos(subcat, url_norm)
            print(f"📁 Subpáginas em '{subcat}': {len(subpaginas)}\n")
            for nome, link in subpaginas:
                link_norm = normalizar_url(link)
                links_extra = extrair_links(link_norm, categoria)
                for t, u in links_extra:
                    all_rows.append({
                        "Categoria": categoria,
                        "Subcategoria": subcat,
                        "Página": nome,
                        "Texto": t,
                        "URL": u
                    })
                if link_norm not in visitados_profundo:
                    visitados_profundo.add(link_norm)
        else:
            # Página raiz da subcategoria
            raiz_links = extrair_links(url_norm, categoria)
            for t, u in raiz_links:
                all_rows.append({
                    "Categoria": categoria,
                    "Subcategoria": subcat,
                    "Página": subcat,
                    "Texto": t,
                    "URL": u
                })
            # seguir alguns internos relevantes sem bloquear reutilização em outros contextos
            for t, sublink in raiz_links:
                if any(x in sublink for x in [
                    "/ensino/", "/servicos/", "/programas-", "/erasmus",
                    "/mobilidade", "/comunidade/", "/investigacao",
                    "/candidatos/", "/quem-somos/", "/investigacao-e-inovacao",
                    "/ecossistema-de-inovacao", "/o-isel", "/plano-para-igualdade-de-genero",
                    "/isel-", "/a-descoberta-do-isel", "/projetos", "/estudantes/",
                    "/alem-aulas/", "/empreendedorismo", "/oportunidades/",
                ]):
                    sublink_norm = normalizar_url(sublink)
                    if sublink_norm in visitados_profundo:
                        continue
                    visitados_profundo.add(sublink_norm)
                    sublinks = extrair_links(sublink_norm, categoria)
                    for st, su in sublinks:
                        all_rows.append({
                            "Categoria": categoria,
                            "Subcategoria": subcat,
                            "Página": t or sublink_norm,
                            "Texto": st,
                            "URL": su
                        })
        time.sleep(0.3)

# ---------------- Gravar Excel ----------------
df = pd.DataFrame(all_rows)
# garantir colunas presentes
for col in ["Categoria", "Subcategoria", "Página", "Texto", "URL"]:
    if col not in df.columns:
        df[col] = ""
# deduplicar apenas por URL + Página dentro do mesmo contexto; permitir repetição entre categorias
df.drop_duplicates(subset=["Categoria", "Subcategoria", "Página", "URL"], inplace=True)
df = df[df["URL"].str.startswith("http")]
df.sort_values(by=["Categoria", "Subcategoria", "Página", "Texto"], inplace=True)
df.to_excel(OUTPUT_FILE, index=False)

print("\n🏁 Varredura concluída!\n")
print(f"📘 Total de cursos processados: {total_cursos}")
print(f"🔗 Total de links recolhidos: {len(df)}")
print(f"📁 Guardado em: {OUTPUT_FILE}")