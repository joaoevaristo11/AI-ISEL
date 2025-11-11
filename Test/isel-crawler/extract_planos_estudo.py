"""
Extrai automaticamente todos os Planos de Estudo do site do ISEL,
incluindo:
 - o conteúdo integral das Fichas de Unidade Curricular (FUC),
 - a Comissão Coordenadora (nomes, perfis e fotos),
 - os Representantes dos Alunos,
 - e os Contactos (emails de coordenação).

Usa Selenium + PyMuPDF + BeautifulSoup.
"""

import json
import time
import fitz  # PyMuPDF
from pathlib import Path
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
from datetime import datetime


# ---------- Configuração ----------
def setup_driver(headless=True):
    """Configura o ChromeDriver em modo headless (sem janela visível)."""
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    if headless:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(25)
    return driver


# ---------- PDF ----------
def extract_pdf_text(pdf_url: str):
    """Faz download temporário de um PDF e extrai o texto integral."""
    try:
        resp = requests.get(pdf_url, timeout=25)
        resp.raise_for_status()

        temp_file = Path("temp_fuc.pdf")
        with open(temp_file, "wb") as f:
            f.write(resp.content)

        text = ""
        with fitz.open(temp_file) as doc:
            for page in doc:
                text += page.get_text("text") + "\n"

        temp_file.unlink(missing_ok=True)
        text = " ".join(text.split())
        return text.strip()

    except Exception as e:
        return f"[ERRO ao extrair PDF: {e}]"


# ---------- Tabelas ----------
def extract_all_tables_from_page(html: str, base_url: str):
    """
    Extrai todas as tabelas de disciplinas e créditos,
    preservando o contexto (Ano, Semestre) e as FUCs.
    """
    soup = BeautifulSoup(html, "html.parser")
    tables_data = []

    year_blocks = soup.find_all("div", class_="title-group")
    all_tables = soup.find_all("table")
    if not all_tables:
        return []

    current_year = None
    table_index = 0

    for element in soup.find_all(["div", "table"]):
        if element.name == "div" and "title-group" in element.get("class", []):
            current_year = element.get_text(strip=True)
            continue

        if element.name == "table":
            table_index += 1
            caption = element.find("caption")
            current_semester = caption.get_text(strip=True) if caption else ""

            headers = [th.get_text(strip=True) for th in element.find_all("th")]
            rows = []

            for tr in element.find_all("tr")[1:]:
                cells = []
                for td in tr.find_all("td"):
                    text = td.get_text(strip=True)
                    link_tag = td.find("a", href=True)
                    link_url = None
                    if link_tag:
                        href = link_tag["href"].strip()
                        link_url = urljoin(base_url, href)
                    cells.append((text, link_url))

                if not cells:
                    continue

                row = {"Ano": current_year, "Semestre": current_semester}
                for i, (text, link) in enumerate(cells):
                    col_name = headers[i] if i < len(headers) else f"col_{i+1}"
                    row[col_name] = text
                    if link and link.lower().endswith(".pdf"):
                        row["FUC_PDF"] = link
                        print(f"      📄 A extrair texto da FUC: {link}")
                        row["FUC_TEXT"] = extract_pdf_text(link)

                rows.append(row)

            tables_data.append({
                "id": table_index,
                "ano": current_year,
                "semestre": current_semester,
                "headers": headers,
                "rows": rows
            })

    return tables_data


# ---------- Comissão Coordenadora, Representantes e Contactos ----------
def extract_comissao_info(soup, base_url):
    """
    Extrai a Comissão Coordenadora, Representantes dos Alunos e Contactos de um curso ISEL.
    Retorna um dicionário com coordenadores, representantes e emails.
    """
    data = {
        "coordenadores": [],
        "representantes": [],
        "contactos": []
    }

    # === Comissão Coordenadora ===
    section_coord = None
    for block in soup.find_all("div", class_="list-coordenador"):
        header = block.find("header")
        if header and "Comissão" in header.get_text():
            section_coord = block
            break

    if section_coord:
        for item in section_coord.select(".view-content-wrap .item"):
            a = item.find("a", href=True)
            nome = a.get_text(strip=True) if a else ""
            perfil = urljoin(base_url, a["href"]) if a else ""
            img_tag = item.find("img")
            foto = urljoin(base_url, img_tag["src"]) if img_tag and img_tag.get("src") else None
            if nome:
                data["coordenadores"].append({
                    "nome": nome,
                    "perfil_url": perfil,
                    "foto": foto
                })

    # === Representantes dos Alunos ===
    section_reps = None
    for block in soup.find_all("div", class_="list-coordenador"):
        header = block.find("header")
        if header and "Representantes" in header.get_text():
            section_reps = block
            break

    if section_reps:
        for div in section_reps.select(".field-content"):
            rep = div.get_text(strip=True)
            if rep:
                data["representantes"].append(rep)

    # === Contactos ===
    section_contacts = None
    for block in soup.find_all("div", class_="list-coordenador"):
        header = block.find("header")
        if header and "Contactos" in header.get_text():
            section_contacts = block
            break

    if section_contacts:
        for a in section_contacts.select("a[href^='mailto:']"):
            email = a.get_text(strip=True)
            if email:
                data["contactos"].append(email)

    return data


# ---------- Principal ----------
def main():
    planos_path = Path("planos_urls.txt")
    if not planos_path.exists():
        print("❌ Ficheiro 'planos_urls.txt' não encontrado. Corre primeiro generate_planos_list.py.")
        return

    with open(planos_path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"✅ {len(urls)} planos de estudo para processar.\n")

    output_file = Path("planos_estudo_fuc_completo.json")
    driver = setup_driver(headless=True)
    results = []

    for i, url in enumerate(urls, start=1):
        print(f"\n[{i}/{len(urls)}] A carregar {url} ...")
        try:
            driver.get(url)
            time.sleep(3)
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # === Extração ultra-robusta do título ===
            title_candidates = [
                soup.select_one("h1.field-content"),
                soup.find("h1"),
                soup.select_one("h1.page-title"),
                soup.select_one("div.page-header h1"),
                soup.select_one("section h1"),
            ]
            title_tag = next((t for t in title_candidates if t and t.get_text(strip=True)), None)
            title_text = title_tag.get_text(strip=True) if title_tag else "Sem título"

            if title_text == "Sem título":
                print("   ⚠️ Atenção: não foi possível encontrar o nome do curso!")
            else:
                print(f"   🎓 Curso encontrado: {title_text}")

            path_parts = urlparse(url).path.strip("/").split("/")
            curso_sigla = next((p for p in path_parts if len(p) <= 6 and p.isalpha()), "")

            # === Extrair tabelas ===
            tables = extract_all_tables_from_page(html, url)
            print(f"   ✅ {len(tables)} tabelas extraídas de {title_text}")

            # === Extrair coordenadores / representantes / contactos ===
            comissao = extract_comissao_info(soup, url)
            if any(comissao.values()):
                print(f"   👥 Comissão Coordenadora e contactos encontrados.")
            else:
                print(f"   ⚠️ Nenhuma comissão encontrada.")

            results.append({
                "url": url,
                "domain": urlparse(url).netloc,
                "curso": title_text,
                "curso_sigla": curso_sigla.lower(),
                "type": "plano_estudos",
                "degree_level": "licenciatura" if "licenciatura" in html.lower() else "desconhecido",
                "crawled_at": datetime.utcnow().isoformat(),
                "tabelas": tables,
                "comissao_coordenadora": comissao
            })

            if i % 3 == 0:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"💾 Progresso guardado ({i}/{len(urls)})")

        except TimeoutException:
            print(f"   ⚠️ Timeout ao carregar {url}")
        except Exception as e:
            print(f"   ❌ Erro em {url}: {e}")

    driver.quit()

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Extração concluída — Ficheiro guardado em: {output_file.resolve()}")


if __name__ == "__main__":
    main()
