import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import time
from collections import defaultdict

# ==========================================
# 1️⃣ Configurações principais
# ==========================================
BASE_URLS = {
    "Licenciaturas": "https://www.isel.pt/cursos/licenciaturas",
    "Mestrados": "https://www.isel.pt/cursos/mestrados",
    "Pós-Graduações": "https://www.isel.pt/cursos/pos-graduacoes",
    "Outros Cursos": "https://www.isel.pt/cursos/outros-cursos"
}

HEADERS = {"User-Agent": "Mozilla/5.0 (AI-ISEL academic crawler)"}

output_excel = "../data/isel_todos_cursos_links.xlsx"

# ==========================================
# 2️⃣ Função auxiliar – Ignorar menus globais
# ==========================================
def is_in_navigation(a_tag, base_path):
    """Determina se o link pertence ao menu global (que deve ser ignorado)."""
    if a_tag.find_parent(['header', 'nav', 'footer', 'aside']):
        return True

    role = a_tag.get('role', '')
    if role and 'navigation' in role.lower():
        return True

    parent = a_tag.parent
    while parent:
        cls = " ".join(parent.get('class', []))
        if any(k in cls.lower() for k in ('menu', 'nav', 'navbar', 'header', 'footer', 'cookie', 'skip')):
            # ✅ exceção: permitir menus internos de curso
            if parent.find_parent(class_="banner-curso") or parent.find_parent(class_="views-field-field-menu"):
                return False
            return True
        parent = parent.parent

    # ⚠️ exceção: se for link interno do mesmo curso (/curso/...), não ignorar
    href = a_tag.get('href', '')
    if href and href.startswith("/curso/") and base_path in href:
        return False

    return False


# ==========================================
# 3️⃣ Função principal – Extrair cursos de uma categoria
# ==========================================
def extrair_links_categoria(tipo_curso, base_url):
    """Extrai todos os cursos e seus links internos para uma categoria."""
    DOMAIN = urlparse(base_url).netloc
    print(f"\n🚀 A aceder à página de {tipo_curso}: {base_url}\n")

    try:
        resp = requests.get(base_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Erro ao aceder à página de {tipo_curso}: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Encontrar todos os links de cursos individuais
    course_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True)
        if not href or not text:
            continue

        full_url = urljoin(base_url, href)
        if "/curso/" in full_url and DOMAIN in full_url:
            course_links.append((text, full_url))

    # Remover duplicados mantendo a ordem
    course_links = list(dict.fromkeys(course_links))
    print(f"🎓 Total de cursos encontrados em {tipo_curso}: {len(course_links)}\n")

    # Extrair links de cada curso
    all_rows = []
    pdf_links = set()

    for course_name, course_url in course_links:
        print(f"🔍 [{tipo_curso}] A processar: {course_name}")

        try:
            resp = requests.get(course_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ Erro ao aceder a {course_url}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

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

            full_url = urljoin(course_url, href)
            parsed = urlparse(full_url)

            # Ignorar links externos (exceto PDFs)
            if parsed.netloc and parsed.netloc != DOMAIN and not full_url.lower().endswith(".pdf"):
                continue

            text = a.get_text(strip=True) or a.get('aria-label') or a.get('title') or ""

            # Ignorar menus globais
            if (not text.strip() and a.find('img')) or is_in_navigation(a, course_url):
                continue

            # Registrar PDF
            if full_url.lower().endswith(".pdf"):
                pdf_links.add(full_url)

            all_rows.append({
                "Tipo de Curso": tipo_curso,
                "Curso": course_name,
                "Texto": text or "(sem texto visível)",
                "URL": full_url
            })

        print(f"   ✅ {len([r for r in all_rows if r['Curso'] == course_name])} links recolhidos.")
        time.sleep(0.5)

    df = pd.DataFrame(all_rows)
    df = df[df["URL"].str.startswith("http")]
    return df


# ==========================================
# 4️⃣ Execução principal – varre todas as categorias
# ==========================================
todas_categorias = []
for tipo, url in BASE_URLS.items():
    df_categoria = extrair_links_categoria(tipo, url)
    todas_categorias.append(df_categoria)

# Unir todos os resultados
df_final = pd.concat(todas_categorias, ignore_index=True)
df_final.drop_duplicates(subset=["Tipo de Curso", "Curso", "URL"], inplace=True)
df_final.sort_values(by=["Tipo de Curso", "Curso", "Texto"], inplace=True)

# Gravar no Excel
df_final.to_excel(output_excel, index=False)

# ==========================================
# 5️⃣ Resultado final
# ==========================================
print("\n🏁 Varredura concluída!\n")
print(f"📘 Total de cursos processados: {df_final['Curso'].nunique()}")
print(f"🔗 Total de links recolhidos: {len(df_final)}")
print(f"📁 Guardado em: {output_excel}")
