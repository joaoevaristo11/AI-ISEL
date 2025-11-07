# run.py
import argparse
from crawler import Crawler, CrawlerConfig


def main():
    p = argparse.ArgumentParser(
        description="Crawler simples para extrair hiperligações (links) e conteúdos de um site."
    )
    p.add_argument("root", help="URL inicial (ex.: https://www.isel.pt)")
    p.add_argument("--depth", type=int, default=2, help="Profundidade máxima (default: 2)")
    p.add_argument("--same-domain", action="store_true", help="Confinar ao domínio (ex.: isel.pt)")
    p.add_argument("--confine-prefix", default=None, help="Obrigar a começar por este prefixo (opcional)")
    p.add_argument("--exclude", action="append", default=[], help="Prefixos a excluir (pode repetir)")
    p.add_argument("--timeout", type=float, default=7.0, help="Timeout por pedido (s)")
    p.add_argument("--delay", type=float, default=0.0, help="Atraso entre pedidos (politeness)")
    p.add_argument("--max-pages", type=int, default=None, help="Limitar número de páginas a visitar")
    p.add_argument("--ua", default="isel-link-extractor/1.0", help="User-Agent")
    p.add_argument("--out", default="links.json", help="Ficheiro de saída (json/csv/dot pela extensão)")

    # 🆕 Novos argumentos
    p.add_argument(
        "--extract-content",
        action="store_true",
        help="Extrair também título, meta description, h1, h2 e texto principal de cada página",
    )
    p.add_argument(
        "--out-content",
        default=None,
        help="Caminho para o ficheiro NDJSON onde guardar os conteúdos extraídos (ex.: pages_content.jsonl)",
    )

    args = p.parse_args()

    cfg = CrawlerConfig(
        user_agent=args.ua,
        timeout=args.timeout,
        delay=args.delay,
        depth_limit=args.depth,
        same_domain=args.same_domain,
        confine_prefix=args.confine_prefix,
        exclude_prefixes=args.exclude,
        max_pages=args.max_pages,
        extract_content=args.extract_content,  # ⬅️ ativa o modo de extração
    )

    cr = Crawler(args.root, cfg)
    cr.crawl()

    out = args.out.lower()
    if out.endswith(".json"):
        cr.to_json(args.out)
        print(f"✅ JSON guardado em {args.out}")
    elif out.endswith(".csv"):
        cr.to_csv(args.out)
        print(f"✅ CSV guardado em {args.out}")
    elif out.endswith(".dot"):
        cr.to_dot(args.out)
        print(f"✅ DOT (Graphviz) guardado em {args.out}")
    else:
        cr.to_json(args.out)
        print(f"ℹ️ extensão não reconhecida — guardei JSON em {args.out}")

    # 📝 Guardar conteúdos (caso ativado)
    if args.extract_content and args.out_content:
        cr.to_jsonl_content(args.out_content)
        print(f"📝 Conteúdos guardados em {args.out_content}")


if __name__ == "__main__":
    main()
