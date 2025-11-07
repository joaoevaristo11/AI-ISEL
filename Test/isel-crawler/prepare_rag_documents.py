"""
Gera um ficheiro otimizado para RAG (Chatbot ISEL) a partir do dataset completo.
Extrai e limpa o texto de cada página (cursos, serviços, notícias, FUCs, etc.)
e cria um único ficheiro rag_documents.json.
"""

import json
from pathlib import Path

def clean_text(text: str) -> str:
    """Remove espaços, quebras e duplicados no texto."""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())
    return text.strip()

def merge_text_fields(page_data: dict) -> str:
    """Combina título, texto e FUCs num só campo para RAG."""
    parts = []
    if page_data.get("titulo"):
        parts.append(page_data["titulo"])
    if page_data.get("texto"):
        parts.append(page_data["texto"])
    if page_data.get("meta_description"):
        parts.append(page_data["meta_description"])
    if page_data.get("fucs"):
        for f in page_data["fucs"]:
            if f.get("texto"):
                parts.append(f["texto"])
    return clean_text(" ".join(parts))

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
            "texto": texto_final,
            "meta_description": data.get("meta_description", ""),
            "h2": data.get("h2", []),
        }

        # Se existirem FUCs associadas, inclui-as
        if "fucs" in data:
            doc["fucs"] = data["fucs"]

        rag_docs.append(doc)

    # Guardar ficheiro
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rag_docs, f, ensure_ascii=False, indent=2)

    print(f"✅ Ficheiro RAG criado com {len(rag_docs)} documentos.")
    print(f"📂 Guardado em: {output_path.resolve()}")

if __name__ == "__main__":
    main()
