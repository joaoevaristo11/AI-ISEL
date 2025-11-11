"""
Constrói a base vetorial Chroma com chunks enriquecidos (anchors/keywords/aliases).
"""

import json, time, uuid
from pathlib import Path
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

DATA_PATH   = Path("rag_documents.json")
CHROMA_PATH = Path("db")
EMBEDDING_MODEL = "nomic-embed-text"
BATCH_SIZE = 1000

def load_documents():
    with open(DATA_PATH,"r",encoding="utf-8") as f:
        data=json.load(f)
    docs=[]
    for item in data:
        url   = item.get("url","")
        title = item.get("titulo","")
        text  = item.get("texto","")
        if not text.strip():
            continue

        base_meta = {
            "url": url,
            "title": title,
            "type": item.get("type",""),
            "curso_nome": item.get("curso_nome",""),
            "degree_level": item.get("degree_level",""),
            "keywords": item.get("keywords",[]),
            "aliases":  item.get("aliases",[]),
            "anchors":  item.get("anchors",[])
        }

        # 🧹 Corrigir metadados inválidos (listas/dicts → strings)
        safe_meta = {}
        for k, v in base_meta.items():
            if isinstance(v, (list, dict)):
                safe_meta[k] = ", ".join(map(str, v))
            else:
                safe_meta[k] = v

        content = f"{title}\n\n{text}"
        docs.append(Document(page_content=content, metadata=safe_meta))
    return docs


def main():
    print("📦 A carregar documentos...")
    docs = load_documents()
    print(f"✅ {len(docs)} documentos carregados.\n")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, chunk_overlap=200,
        separators=["\n📘 ","\n📄 ","\n- ", "\n\n", "\n", " "]
    )
    split_docs = splitter.split_documents(docs)
    # atribuir ids únicos e propagar anchors como texto extra (boost leve)
    enriched=[]
    for d in split_docs:
        meta = dict(d.metadata)
        anchors = meta.get("anchors",[])
        if anchors:
            d.page_content = d.page_content + "\n\n" + "\n".join(anchors[:10])
        meta["chunk_id"] = str(uuid.uuid4())
        enriched.append(Document(page_content=d.page_content, metadata=meta))

    print(f"✅ {len(enriched)} segmentos prontos para indexação.\n")
    embedding_fn = OllamaEmbeddings(model=EMBEDDING_MODEL)
    vectordb = Chroma(persist_directory=str(CHROMA_PATH), embedding_function=embedding_fn)

    total_batches = (len(enriched)+BATCH_SIZE-1)//BATCH_SIZE
    for i in tqdm(range(total_batches), desc="🔄 Indexar batches", unit="batch"):
        batch = enriched[i*BATCH_SIZE : min((i+1)*BATCH_SIZE, len(enriched))]
        vectordb.add_documents(batch)
        try: vectordb._client.persist()
        except Exception: pass
        time.sleep(0.1)

    print(f"\n✅ Base vetorial criada em: {CHROMA_PATH.resolve()}")
    print("📊 Pronta para consultas RAG.")

if __name__ == "__main__":
    main()
