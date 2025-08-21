"""Búsqueda web simple para responder preguntas desde Internet.

Usa duckduckgo_search para obtener resultados textuales (título, enlace, snippet)
y construye una respuesta breve en español con 1-3 fuentes.

Dependencias: duckduckgo_search
"""
from __future__ import annotations

from typing import List


def search_and_answer(query: str, max_results: int = 3) -> str:
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except Exception:
        return "Para responder con Internet necesito instalar 'duckduckgo_search'. Añádelo a requirements e instala las dependencias."

    query = query.strip()
    if not query:
        return "¿Qué quieres buscar?"

    try:
        res: List[dict] = []
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=max_results)):  # type: ignore
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
        partes.append(f"Según la web: {snippet}")
        partes.append(f"Fuente principal: {first['title']} — {first['href']}")
        if len(res) > 1:
            extras = [f"{i+2}. {r['title']} — {r['href']}" for i, r in enumerate(res[1:])]
            partes.append("Más fuentes:\n" + "\n".join(extras))

        return "\n\n".join(partes)
    except Exception as e:
        return f"Hubo un problema al buscar en Internet: {e}"
