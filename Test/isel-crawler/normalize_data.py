"""
Normaliza e unifica os ficheiros num dataset coerente (dataset_isel_completo.json),
criando também tags e aliases de pesquisa para melhorar a recuperação no RAG.
"""

import json, csv, argparse
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

def load_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Ficheiro não encontrado: {p}"); return []
    except Exception as e:
        print(f"⚠️ Erro a ler {p}: {e}"); return []

def load_jsonl(p):
    out=[]
    try:
        with open(p, "r", encoding="utf-8") as f:
            for ln in f:
                if ln.strip(): out.append(json.loads(ln))
    except FileNotFoundError:
        print(f"⚠️ Ficheiro não encontrado: {p}")
    return out

def normalize_url(url: str):
    if not url: return ""
    url = url.strip().replace("http://","https://")
    url = url.split("#")[0]
    return url[:-1] if url.endswith("/") else url

def clean_and_enrich_links(links):
    """
    Remove duplicados, ignora links externos irrelevantes e melhora textos vazios.
    """
    cleaned = []
    seen = set()

    EXCLUDE_DOMAINS = [
        "flickr.com",
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "linkedin.com",
        "moodle.isel.pt",
        "portal.ipl.pt",
        "sharepoint.com",
        "net.ipl.pt",
        "repositorio.ipl.pt",
        "agendacultural.ipl.pt",
        "ano.pt",
        "ipl.pt",
        "estesl.ipl.pt",
        "esml.ipl.pt",
        "esd.ipl.pt",
        "eselx.ipl.pt",
        "escs.ipl.pt",
        "estc.ipl.pt",
    ]

    for l in links:
        url = (l.get("url") or "").strip()
        text = (l.get("text") or "").strip()
        if not url or url in seen:
            continue

        domain = urlparse(url).netloc.lower()
        if any(d in domain for d in EXCLUDE_DOMAINS):
            # ignora domínios externos sem relevância direta para o ISEL
            continue

        seen.add(url)

        if not text:
            # tenta extrair um nome mais legível a partir do URL
            last_seg = url.rstrip("/").split("/")[-1]
            text = last_seg.replace("-", " ").capitalize() if last_seg else "Link"

        cleaned.append({"text": text, "url": url})

    return cleaned


def classify_page_type(url: str) -> str:
    u = url.lower()
    if "/curso/" in u and "/plano-de-estudos" in u: return "plano_estudos"
    if "/curso/" in u: return "curso"
    if "/noticias/" in u or "/news/" in u: return "noticia"
    if "/candidatos/" in u or "propinas" in u or "calendario" in u: return "admissao"
    if "/servicos/" in u or "/comunidade/" in u: return "servico"
    if "/o-isel" in u or "/about" in u: return "institucional"
    return "outro"

# Helpers para tags/aliases
def degree_from_title(title: str):
    t = (title or "").lower()
    if "licenciatura" in t: return "licenciatura"
    if "mestrado" in t: return "mestrado"
    if "pós" in t or "pos-" in t or "especialização" in t: return "posgraduacao"
    return ""

def build_aliases_and_tags(record: dict):
    title = record.get("titulo","") or record.get("curso_nome","") or ""
    tlow = title.lower()
    tags, aliases = set(), set()

    # tags por grau
    deg = record.get("degree_level") or degree_from_title(title)
    if deg: tags.add(deg)

    # tags por tipo
    t = record.get("type","")
    if t: tags.add(t)

    # aliases por curso
    if title:
        aliases.add(title)
        # versões sem acentos/simplificadas (mínimo)
        aliases.add(title.replace("Informática", "Informatica"))

    # tags por áreas frequentes
    area_hints = ["informática","computadores","eletrónica","mecânica","química","civil","telecomunicações"]
    for a in area_hints:
        if a in tlow: tags.add(a)

    # se houver tabelas com Ano/Semestre, marca
    if record.get("tabelas"):
        tags.update({"plano","tabelas","ano_semestre"})

    return sorted(tags), sorted(aliases)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true")
    args = ap.parse_args()

    base = Path(".")
    out_json = base/"dataset_isel_completo.json"
    out_csv  = base/"dataset_isel_completo.csv"

    links_data       = load_json(base/"links.json")
    pages_data       = load_jsonl(base/"pages_content.jsonl")
    hyperlinks_data  = load_json(base/"hyperlinks.json")
    planos_data      = load_json(base/"planos_estudo_fuc_completo.json")

    dataset = {}

    # 1) páginas com conteúdo
    for page in pages_data:
        url = normalize_url(page.get("url"))
        if not url: continue
        dataset.setdefault(url, {})
        d = dataset[url]
        d["titulo"] = page.get("title","")
        d["texto"]  = page.get("text","")
        d["h1"]     = page.get("h1","")
        d["h2"]     = page.get("h2",[])
        d["meta_description"] = page.get("meta_description","")
        d["lang"]   = page.get("lang","")
        d["domain"] = page.get("domain") or urlparse(url).netloc
        d["type"]   = page.get("type") or classify_page_type(url)
        d["curso_nome"] = page.get("curso_nome","")
        d["crawled_at"] = page.get("crawled_at", datetime.utcnow().isoformat())

    # 2) hyperlinks
    for item in hyperlinks_data:
        page = normalize_url(item.get("page"))
        dataset.setdefault(page, {})
        existing = dataset[page].get("links",[])
        dataset[page]["links"] = clean_and_enrich_links(existing + item.get("links",[]))

    # 3) planos + FUCs (com ano/semestre)
    for plano in planos_data:
        url = normalize_url(plano.get("url"))
        if not url: continue
        dataset.setdefault(url, {})
        d = dataset[url]
        d["curso_nome"]   = plano.get("curso","")
        d["type"]         = "plano_estudos"
        d["degree_level"] = plano.get("degree_level","desconhecido")
        d["tabelas"]      = plano.get("tabelas",[])
        fucs=[]
        for tab in plano.get("tabelas",[]):
            for row in tab.get("rows",[]):
                if "FUC_PDF" in row:
                    fucs.append({
                        "pdf": row["FUC_PDF"],
                        "texto": row.get("FUC_TEXT",""),
                        "ano": row.get("Ano",""),
                        "semestre": row.get("Semestre","")
                    })
        if fucs: d["fucs"]=fucs

    # 4) ligar curso <-> plano
    print("🔗 A ligar cursos aos seus planos de estudo...")
    for plano in planos_data:
        plano_url  = normalize_url(plano.get("url"))
        curso_nome = (plano.get("curso","") or "").lower()
        best = None
        for page_url, data in dataset.items():
            if data.get("type")!="curso": continue
            titulo = (data.get("titulo","") or "").lower()
            if curso_nome and curso_nome.split("engenharia")[-1].strip() in titulo:
                best = data; break
        if best:
            dataset[plano_url]["curso_nome_relacionado"] = best.get("titulo","")
            best["plano_de_estudos_url"]   = plano_url
            best["plano_de_estudos_curso"] = plano.get("curso","")
            print(f"   🔗 Ligado: {best.get('titulo','')} → {plano_url}")

    # 5) links globais dos crawls
    if isinstance(links_data, dict) and "pages" in links_data:
        for page, out_links in links_data["pages"].items():
            page_norm = normalize_url(page)
            dataset.setdefault(page_norm, {})
            links = [{"text":"","url":normalize_url(l)} for l in out_links]
            dataset[page_norm]["links"] = clean_and_enrich_links(dataset[page_norm].get("links",[]) + links)

    # 6) limpeza e criação de tags/aliases
    print("\n🧹 A normalizar e etiquetar...")
    for url, data in dataset.items():
        if "links" in data:
            data["links"] = clean_and_enrich_links(data["links"])
        tags, aliases = build_aliases_and_tags(data)
        if tags: data["tags"]=tags
        if aliases: data["search_aliases"]=aliases

    with open(out_json,"w",encoding="utf-8") as f:
        json.dump(dataset,f,ensure_ascii=False,indent=2)

    print(f"\n✅ Dataset final guardado em: {out_json.resolve()}")
    print(f"📊 Total de páginas integradas: {len(dataset)}")

    if args.csv:
        print("🧾 A gerar CSV...")
        with open(out_csv,"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f)
            w.writerow(["URL","Tipo","Título","Curso Nome","Plano de Estudos","Idioma","Links","FUCs","Tags"])
            for url, data in dataset.items():
                w.writerow([
                    url,
                    data.get("type",""),
                    data.get("titulo",""),
                    data.get("curso_nome",""),
                    data.get("plano_de_estudos_url",""),
                    data.get("lang",""),
                    len(data.get("links",[])),
                    len(data.get("fucs",[])) if "fucs" in data else 0,
                    "|".join(data.get("tags",[]))
                ])
        print(f"✅ CSV exportado para: {out_csv.resolve()}")

if __name__ == "__main__":
    main()
