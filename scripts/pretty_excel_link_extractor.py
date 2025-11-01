import pandas as pd
from urllib.parse import urlparse

# 1️⃣ Carrega o ficheiro CSV com todos os links
df = pd.read_csv("../data/isel_links_hierarquico.csv")

# 2️⃣ Normaliza e separa cada URL em partes
def extract_path_parts(url):
    path = urlparse(url).path.strip("/")
    parts = [p for p in path.split("/") if p and p not in ("pt", "en")]
    return parts

rows = []
for url in df["URL"]:
    parts = extract_path_parts(url)
    row = {"URL": url}
    for i, p in enumerate(parts, start=1):
        row[f"Nível {i}"] = p
    rows.append(row)

# 3️⃣ Cria novo DataFrame com colunas flexíveis
df_hier = pd.DataFrame(rows)

# Ajusta nomes das colunas para serem mais "semânticas"
max_depth = len([c for c in df_hier.columns if c.startswith("Nível")])

col_names = ["Grupo", "Subgrupo", "Sub-subgrupo", "Sub-sub-subgrupo", "Sub-sub-sub-subgrupo"]
# corta ou expande conforme a profundidade encontrada
rename_map = {f"Nível {i+1}": (col_names[i] if i < len(col_names) else f"Nível {i+1}") for i in range(max_depth)}
df_hier.rename(columns=rename_map, inplace=True)

# 4️⃣ Ordena pela hierarquia (para ficar agrupado no Excel)
sort_cols = [c for c in df_hier.columns if c != "URL"]
df_hier = df_hier.sort_values(by=sort_cols, na_position="last")

# 5️⃣ Exporta para Excel (melhor que CSV neste caso)
output_file = "../data/isel_site_tree.xlsx"
df_hier.to_excel(output_file, index=False, engine="openpyxl")

print(f"✅ Hierarquia criada com sucesso!")
print(f"📁 Ficheiro: {output_file}")
print(f"📊 Total de linhas: {len(df_hier)}")
