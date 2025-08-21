"""Búsqueda web en español con DuckDuckGo y soporte opcional para Google.

- Respuestas breves en español con 1-3 fuentes.
- Prioriza resultados en español (región es-ES cuando aplica).
- Soporte opcional a Google (enlaces) si está instalado `googlesearch-python`.
"""
from __future__ import annotations

from typing import List, Tuple


def search_and_answer(query: str, max_results: int = 3, provider: str = "ddg") -> str:
    """Busca respuesta breve en español.

    provider: "ddg" (por defecto) resume con DuckDuckGo; "google" devuelve
    una respuesta breve y enlaces usando googlesearch si está disponible.
    """
    query = (query or "").strip()
    if not query:
        return "¿Qué quieres buscar?"

    if provider.lower() == "google":
        enlaces = google_links(query, max_results=max_results)
        if not enlaces:
            # Fallback a DDG si Google no está disponible
            return _ddg_answer(query, max_results)
        partes: List[str] = [
            "Resultados (Google) en español:",
            *[f"{i+1}. {t} — {u}" for i, (t, u) in enumerate(enlaces)],
        ]
        return "\n".join(partes)

    return _ddg_answer(query, max_results)


def _ddg_answer(query: str, max_results: int) -> str:
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except Exception:
        return (
            "Para responder con Internet necesito instalar 'duckduckgo_search'. "
            "Añádelo a requirements e instala las dependencias."
        )

    try:
        res: List[dict] = []
        # Forzar región española para priorizar contenido en ES
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, region="es-es", safesearch="moderate", max_results=max_results)):  # type: ignore
                if not isinstance(r, dict):
                    continue
                title = (r.get("title") or "").strip()
                href = (r.get("href") or "").strip()
                body = (r.get("body") or "").strip()
                if title and href:
                    res.append({"title": title, "href": href, "body": body})
                if len(res) >= max_results:
                    break

        if not res:
            return "No encontré resultados relevantes en la web. Intenta reformular tu pregunta."

        # Construir una respuesta breve con el primer resultado + enlaces extra
        first = res[0]
        snippet = first.get("body") or ""
        if len(snippet) > 280:
            snippet = snippet[:277].rstrip() + "…"

        partes: List[str] = []
        partes.append(f"Según la web (español): {snippet}")
        partes.append(f"Fuente principal: {first['title']} — {first['href']}")
        if len(res) > 1:
            extras = [f"{i+2}. {r['title']} — {r['href']}" for i, r in enumerate(res[1:])]
            partes.append("Más fuentes:\n" + "\n".join(extras))

        return "\n\n".join(partes)
    except Exception as e:
        return f"Hubo un problema al buscar en Internet: {e}"


def google_links(query: str, max_results: int = 3) -> List[Tuple[str, str]]:
    """Obtiene enlaces de Google (si hay librería disponible). Devuelve lista (título, url)."""
    try:
        from googlesearch import search  # type: ignore
    except Exception:
        return []
    out: List[Tuple[str, str]] = []
    try:
        # lang es para priorizar resultados en español; tld y country pueden ayudar
        for url in search(query, num_results=max_results, lang="es", advanced=True):  # type: ignore
            try:
                title = getattr(url, "title", "") or "Resultado"
                link = getattr(url, "url", None) or str(url)
                out.append((title.strip(), link.strip()))
            except Exception:
                continue
            if len(out) >= max_results:
                break
    except Exception:
        return []
    return out
