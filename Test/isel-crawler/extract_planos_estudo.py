"""
Extrai automaticamente todos os Planos de Estudo do site do ISEL,
incluindo o conteúdo integral dos PDFs (Fichas de Unidade Curricular - FUC),
usando Selenium + PyMuPDF.

⚙️ Requisitos:
    - planos_urls.txt (lista gerada por generate_planos_list.py)
    - Chrome + webdriver_manager + PyMuPDF instalados
"""

import json
import time
import fitz  # PyMuPDF
from pathlib import Path
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests


def setup_driver(headless=True):
    """Configura o Chrome headless."""
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    if headless:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(20)
    return driver


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


def extract_all_tables_from_page(html: str, base_url: str):
    """Extrai todas as tabelas (disciplinas, créditos, etc.), incluindo PDFs das FUC."""
    soup = BeautifulSoup(html, "html.parser")
    tables_data = []

    tables = soup.find_all("table")
    if not tables:
        return []

    for idx, table in enumerate(tables, start=1):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows = []

        for tr in table.find_all("tr")[1:]:
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

            row = {}
            for i, (text, link) in enumerate(cells):
                col_name = headers[i] if i < len(headers) else f"col_{i+1}"
                row[col_name] = text
                if link and link.lower().endswith(".pdf"):
                    row["FUC_PDF"] = link
                    print(f"      📄 A extrair texto da FUC: {link}")
                    row["FUC_TEXT"] = extract_pdf_text(link)

            rows.append(row)

        tables_data.append({
            "id": idx,
            "headers": headers,
            "rows": rows
        })

    return tables_data


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

            title = soup.find("h1")
            title_text = title.get_text(strip=True) if title else "Sem título"

            tables = extract_all_tables_from_page(html, url)
            print(f"   ✅ {len(tables)} tabelas extraídas de {title_text}")

            results.append({
                "url": url,
                "curso": title_text,
                "tabelas": tables
            })

            # Guarda progresso incremental (a cada 3 páginas)
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
