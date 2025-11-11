"""
Gera um ficheiro otimizado para RAG (Chatbot AI-ISEL) a partir do dataset completo.
Inclui planos de estudo, FUCs e metadados úteis (curso_nome, tipo, grau, etc.),
e organiza também a informação da Comissão Coordenadora, Representantes e Contactos.
"""

import json
from pathlib import Path


# ---------- Limpeza de texto ----------
def clean_text(text: str) -> str:
    """Remove espaços, quebras e duplicações."""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())
    return text.strip()


# ---------- Planos de Estudo ----------
def extract_planos_text(page_data: dict) -> str:
    """Extrai e formata o texto das tabelas dos planos de estudo (Ano / Semestre / Disciplinas)."""
    if not page_data.get("tabelas"):
        return ""

    parts = []
    for tab in page_data["tabelas"]:
        ano = tab.get("ano", "")
        semestre = tab.get("semestre", "")
        rows = tab.get("rows", [])

        if ano or semestre:
            parts.append(f"\n📘 {ano} — {semestre}\n")

        for row in rows:
            nome = (
                row.get("Unidade Curricular")
                or row.get("Disciplina")
                or row.get("Área científica")
                or row.get("col_1")
            )
            ects = row.get("ECTS") or row.get("ECTS Obrigatórios") or ""
            area = row.get("Área científica") or ""
            fuc = row.get("FUC_TEXT", "")

            linha = f"- {nome or 'UC'} ({area}) — {ects} ECTS"
            parts.append(linha)

            # Adicionar texto das FUCs, se existir
            if fuc and len(fuc) > 30:
                parts.append(f"\n📄 Ficha UC: {clean_text(fuc[:1200])}")

    return clean_text(" ".join(parts))


# ---------- Comissão Coordenadora ----------
def extract_comissao_text(page_data: dict) -> str:
    """Formata os dados da comissão coordenadora para o texto RAG."""
    if not page_data.get("comissao_coordenadora"):
        return ""

    c = page_data["comissao_coordenadora"]
    parts = []

    # Coordenadores
    if c.get("coordenadores"):
        nomes = ", ".join(p.get("nome", "") for p in c["coordenadores"] if p.get("nome"))
        parts.append(f"👥 Comissão Coordenadora: {nomes}")

    # Representantes
    if c.get("representantes"):
        parts.append(f"🎓 Representantes dos alunos: {', '.join(c['representantes'])}")

    # Contactos
    if c.get("contactos"):
        parts.append(f"📧 Contactos da coordenação: {', '.join(c['contactos'])}")

    return clean_text(" ".join(parts))


# ---------- Fusão de texto ----------
def merge_text_fields(page_data: dict) -> str:
    """Combina título, texto principal, plano de estudos, comissão e metadados relevantes."""
    parts = []

    # 🔹 Conteúdo geral da página
    for k in ("titulo", "texto", "meta_description"):
        if page_data.get(k):
            parts.append(page_data[k])

    # 🔹 Texto estruturado dos planos
    planos_text = extract_planos_text(page_data)
    if planos_text:
        parts.append(planos_text)

    # 🔹 Informação da comissão coordenadora
    comissao_text = extract_comissao_text(page_data)
    if comissao_text:
        parts.append(comissao_text)

    # 🔹 Se existir link para plano de estudos
    if page_data.get("plano_de_estudos_url"):
        parts.append(f"Plano de estudos disponível em: {page_data['plano_de_estudos_url']}")

    # 🔹 Texto das FUCs (extra das tabelas)
    if page_data.get("fucs"):
        for f in page_data["fucs"]:
            if f.get("texto"):
                parts.append(f["texto"])

    # 🔹 Informação de curso e grau
    if page_data.get("curso_nome"):
        parts.append(f"Curso: {page_data['curso_nome']}")
    if page_data.get("degree_level"):
        parts.append(f"Grau: {page_data['degree_level']}")

    return clean_text(" ".join(parts))


# ---------- Principal ----------
def main():
    base_dir = Path(".")
    input_path = base_dir / "dataset_isel_completo.json"
    output_path = base_dir / "rag_documents.json"

    print("📦 A carregar dataset completo...")
    with open(input_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    print(f"✅ {len(dataset)} páginas carregadas.\n")

    rag_docs = []

    for url, data in dataset.items():
        texto_final = merge_text_fields(data)
        if not texto_final:
            continue  # ignora páginas vazias

        doc = {
            "url": url,
            "titulo": data.get("titulo", ""),
            "type": data.get("type", ""),
            "curso_nome": data.get("curso_nome", ""),
            "degree_level": data.get("degree_level", ""),
            "plano_de_estudos_url": data.get("plano_de_estudos_url", ""),
            "texto": texto_final,
            "meta_description": data.get("meta_description", ""),
            "h1": data.get("h1", ""),
            "h2": data.get("h2", []),
            "lang": data.get("lang", ""),
            "domain": data.get("domain", ""),
        }

        # Incluir FUCs, se existirem
        if "fucs" in data:
            doc["fucs"] = data["fucs"]

        # Incluir Comissão Coordenadora (para enriquecer o RAG)
        if "comissao_coordenadora" in data:
            doc["comissao_coordenadora"] = data["comissao_coordenadora"]

        rag_docs.append(doc)

    # Guardar resultado final
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rag_docs, f, ensure_ascii=False, indent=2)

    print(f"✅ Ficheiro RAG criado com {len(rag_docs)} documentos.")
    print(f"📂 Guardado em: {output_path.resolve()}")


if __name__ == "__main__":
    main()
