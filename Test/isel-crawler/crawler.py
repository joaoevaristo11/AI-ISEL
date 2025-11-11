# crawler.py (versão otimizada AI-ISEL)
from __future__ import annotations

import time
import json
import csv
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional
from urllib.parse import urlparse, urljoin
from datetime import datetime

import requests
from requests import Session
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import tldextract


# ---------- utilitários ----------
def same_registrable_domain(a: str, b: str) -> bool:
    ea = tldextract.extract(a)
    eb = tldextract.extract(b)
    if not ea.registered_domain or not eb.registered_domain:
        return False
    return ea.registered_domain == eb.registered_domain


def is_probably_html(resp: requests.Response) -> bool:
    ctype = resp.headers.get("Content-Type", "").lower()
    return "text/html" in ctype or "application/xhtml+xml" in ctype or ctype == ""


@dataclass
class CrawlerConfig:
    user_agent: str = "isel-link-extractor/1.0"
    timeout: float = 7.0
    delay: float = 0.0
    depth_limit: int = 2
    same_domain: bool = True
    confine_prefix: Optional[str] = None
    exclude_prefixes: List[str] = field(default_factory=list)
    max_pages: Optional[int] = None
    extract_content: bool = False  # ⬅️ ativa extração de texto


# ---------- classe principal ----------
class Crawler:
    def __init__(self, root_url: str, config: CrawlerConfig):
        self.root = root_url.rstrip("/")
        self.cfg = config
        self.session: Session = requests.Session()
        self.session.headers.update({"User-Agent": self.cfg.user_agent})

        self.visited: Set[str] = set()
        self.discovered: Dict[str, List[str]] = {}
        self.errors: Dict[str, str] = {}
        self.page_content: Dict[str, Dict] = {}

        self.root_domain = tldextract.extract(self.root).registered_domain
        self.root_netloc = urlparse(self.root).netloc

    # ---------- helpers ----------
    def _should_follow(self, url: str) -> bool:
        if self.cfg.max_pages and len(self.visited) >= self.cfg.max_pages:
            return False
        if url in self.visited:
            return False
        if self.cfg.confine_prefix and not url.startswith(self.cfg.confine_prefix):
            return False
        for p in self.cfg.exclude_prefixes:
            if url.startswith(p):
                return False
        if self.cfg.same_domain:
            try:
                if not same_registrable_domain(url, self.root):
                    return False
            except Exception:
                return False
        return True

    def _normalize_links(self, base_url: str, soup: BeautifulSoup) -> List[str]:
        """Extrai e limpa links de uma página HTML, filtrando duplicados e lixo."""
        out: Set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if not href:
                continue
            if href.startswith("#") or href.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            bad_exts = (
                ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico",
                ".webp", ".zip", ".rar", ".7z", ".mp4", ".mp3", ".css",
                ".js", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"
            )
            if any(href.lower().endswith(ext) for ext in bad_exts):
                continue
            if "?page=" in href.lower() or "?p=" in href.lower():
                continue
            abs_url = urljoin(base_url, href)
            parsed = urlparse(abs_url)
            if parsed.scheme not in ("http", "https"):
                continue
            clean_url = abs_url.split("#")[0]
            out.add(clean_url)
        return sorted(out)

    # ---------- classificação ----------
    def _classify_page_type(self, url: str) -> str:
        """Classifica página com base no URL (tipo semântico)."""
        u = url.lower()
        if "/curso/" in u and "/plano-de-estudos" in u:
            return "plano_estudos"
        elif "/curso/" in u:
            return "curso"
        elif "/noticias/" in u or "/news/" in u:
            return "noticia"
        elif "/candidatos/" in u or "propinas" in u or "calendario" in u:
            return "admissao"
        elif "/servicos/" in u or "/comunidade/" in u:
            return "servico"
        elif "/o-isel" in u or "/about" in u:
            return "institucional"
        else:
            return "outro"

    # ---------- limpeza e extração ----------
    def _clean_dom(self, soup: BeautifulSoup) -> BeautifulSoup:
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        for tag in soup.find_all(["header", "nav", "footer", "aside"]):
            tag.decompose()
        return soup

    def _extract_content_from_soup(self, soup: BeautifulSoup, base_url: str) -> Dict:
        title = (soup.title.string.strip() if soup.title and soup.title.string else "")
        meta_desc = ""
        md = soup.find("meta", attrs={"name": "description"})
        if md and md.get("content"):
            meta_desc = md["content"].strip()

        html_tag = soup.find("html")
        lang = (html_tag.get("lang") or "").strip().lower() if html_tag else ""

        candidates = [
            soup.select_one("main#main-content"),
            soup.select_one("main[role=main]"),
            soup.select_one("main"),
            soup.select_one("article"),
            soup.select_one("div#content"),
            soup.select_one("div.region-content"),
        ]
        container = next((c for c in candidates if c), soup.body or soup)

        h1 = (container.find("h1").get_text(" ", strip=True) if container.find("h1") else "")
        h2 = [h.get_text(" ", strip=True) for h in container.find_all("h2")[:10]]

        self._clean_dom(container)
        text = container.get_text("\n", strip=True)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        cleaned_lines = [ln for ln in lines if len(ln) > 2 and not ln.lower().startswith("isel - instituto")]
        text_clean = "\n".join(cleaned_lines)
        if len(text_clean) > 10000:
            text_clean = text_clean[:10000] + " …"

        return {
            "url": base_url,
            "domain": urlparse(base_url).netloc,
            "type": self._classify_page_type(base_url),
            "crawled_at": datetime.utcnow().isoformat(),
            "title": title,
            "meta_description": meta_desc,
            "h1": h1,
            "h2": h2,
            "lang": lang,
            "text": text_clean,
        }

    # ---------- main ----------
    def crawl(self) -> None:
        q: deque = deque()
        q.append((self.root, 0))

        while q:
            url, depth = q.popleft()
            if depth > self.cfg.depth_limit:
                continue
            if not self._should_follow(url):
                continue
            if self.cfg.delay > 0:
                time.sleep(self.cfg.delay)

            try:
                resp = self.session.get(url, timeout=self.cfg.timeout, allow_redirects=True)
                resp.raise_for_status()
            except RequestException as e:
                self.errors[url] = str(e)
                self.visited.add(url)
                continue

            final_url = str(resp.url)
            if not is_probably_html(resp):
                self.visited.add(final_url)
                self.discovered.setdefault(final_url, [])
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            links = self._normalize_links(final_url, soup)

            self.visited.add(final_url)
            self.discovered[final_url] = links

            if self.cfg.extract_content:
                try:
                    content = self._extract_content_from_soup(soup, final_url)
                    self.page_content[final_url] = {"status": "ok", **content}
                except Exception as e:
                    self.page_content[final_url] = {"status": "error", "url": final_url, "error_msg": str(e)}

            next_depth = depth + 1
            for link in links:
                if next_depth <= self.cfg.depth_limit and self._should_follow(link):
                    q.append((link, next_depth))

            if self.cfg.max_pages and len(self.visited) >= self.cfg.max_pages:
                break

        # ---------- limpeza final ----------
        print("\n🔹 A limpar duplicados globais e normalizar URLs...")
        unique_links = set()
        for page, links in list(self.discovered.items()):
            normalized_links = []
            for link in links:
                clean = link.rstrip("/").split("?")[0].lower()
                if clean not in unique_links:
                    unique_links.add(clean)
                    normalized_links.append(clean)
            self.discovered[page] = normalized_links
        print(f"✅ Total de links únicos globais: {len(unique_links)}\n")

    # ---------- export ----------
    def to_json(self, path: str) -> None:
        payload = {
            "root": self.root,
            "config": self.cfg.__dict__,
            "pages": self.discovered,
            "errors": self.errors,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def to_csv(self, path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["page", "link"])
            for page, links in self.discovered.items():
                if not links:
                    w.writerow([page, ""])
                else:
                    for l in links:
                        w.writerow([page, l])

    def to_dot(self, path: str) -> None:
        def safe(s: str) -> str:
            return s.replace('"', '\\"')
        with open(path, "w", encoding="utf-8") as f:
            f.write("digraph G {\n")
            f.write('  graph [overlap=false];\n  node [shape=box];\n')
            for src, links in self.discovered.items():
                for dst in links:
                    f.write(f'  "{safe(src)}" -> "{safe(dst)}";\n')
            f.write("}\n")

    def to_jsonl_content(self, path: str) -> None:
        """Guarda um objeto por linha com o conteúdo de cada página (NDJSON)."""
        with open(path, "w", encoding="utf-8") as f:
            for _, obj in self.page_content.items():
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
