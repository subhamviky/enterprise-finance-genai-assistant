"""The customer's documents: a small search over synthetic policy documents (GCP-02 Phase C, item 9).

  policies/documents/*.md            shared by every tenant
  policies/documents/<tenant>/*.md   that tenant's own (a tenant never sees another's)

Each `##` section is a passage. Search is lexical (BM25 over the words, no embeddings): it needs no model, no account
and no network, it is deterministic, and on a corpus this size it ranks as well as a vector index would; the same
`search()` would sit in front of a vector store when the corpus is large. A passage becomes an evidence item with an
identifier `doc:<scope>/<file>#<section>`, so an answer built from it cites it like any other record, and a number
the answer states must occur in the passage (the investigator's grounding check)."""
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from .evidence import item

STOP = set("a an the of to in on for and or is are was were be by with what how does do it its this that at as from "
           "my our can may i we you".split())
WORD = re.compile(r"[a-z0-9]+")


def words(text: str) -> List[str]:
    """Lower-cased words, without stop words and with a plural 's' removed (limits, limit)."""
    out = []
    for w in WORD.findall(text.lower()):
        if w in STOP or len(w) < 2:
            continue
        out.append(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


class Passage:
    def __init__(self, scope: str, file: str, title: str, heading: str, text: str):
        self.scope, self.heading, self.text = scope, heading, text
        slug = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
        self.key = f"{scope}/{file}#{slug}"
        self.title = title
        self.tokens = Counter(words(f"{title} {heading} {heading} {text}"))     # the heading counts double
        self.length = sum(self.tokens.values())


def read(path: Path, scope: str) -> List[Passage]:
    title, heading, body, passages = path.stem, None, [], []
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
        elif line.startswith("## "):
            if heading and body:
                passages.append(Passage(scope, path.stem, title, heading, " ".join(body)))
            heading, body = line[3:].strip(), []
        elif line.strip() and heading:
            body.append(line.strip())
    if heading and body:
        passages.append(Passage(scope, path.stem, title, heading, " ".join(body)))
    return passages


class DocumentStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.passages: List[Passage] = []
        if self.root.is_dir():
            for path in sorted(self.root.glob("*.md")):
                self.passages += read(path, "shared")
            for folder in sorted(p for p in self.root.iterdir() if p.is_dir()):
                for path in sorted(folder.glob("*.md")):
                    self.passages += read(path, folder.name)

    def visible(self, tenant: str) -> List[Passage]:
        return [p for p in self.passages if p.scope in ("shared", tenant)]

    def search(self, tenant: str, query: str, k: int = 3) -> List[Dict]:
        """The k best passages for the query among those the tenant may see, as evidence items; none if nothing
        shares a word with the query."""
        pool = self.visible(tenant)
        terms = set(words(query))
        if not pool or not terms:
            return []
        n, average = len(pool), sum(p.length for p in pool) / len(pool)
        scored = []
        for p in pool:
            score = 0.0
            for term in terms:
                f = p.tokens.get(term, 0)
                if not f:
                    continue
                df = sum(1 for q in pool if term in q.tokens)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                score += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * p.length / average))
            if score > 0:
                scored.append((score, p))
        scored.sort(key=lambda sp: (-sp[0], sp[1].key))
        return [item("doc", p.key, f"{p.title}, {p.heading}: {p.text[:700]}",
                     {"scope": p.scope, "title": p.title, "heading": p.heading, "text": p.text, "score": round(s, 3)})
                for s, p in scored[:k]]


@lru_cache(maxsize=4)
def _store(root: str) -> DocumentStore:
    return DocumentStore(Path(root))


def store() -> DocumentStore:
    default = Path(__file__).resolve().parents[3] / "policies" / "documents"
    return _store(os.getenv("GENAI_DOCUMENTS_DIR") or str(default))
