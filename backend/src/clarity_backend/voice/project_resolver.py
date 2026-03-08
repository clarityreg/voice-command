"""Resolve spoken project names to Plane project IDs.

Two-tier approach:
1. Exact/fuzzy match against aliases and project names (instant, offline)
2. Local LLM fallback via Ollama for ambiguous cases (3s timeout)
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
FUZZY_THRESHOLD = 0.6

SYSTEM_PROMPT = """You are a voice command project resolver. Given a spoken name and a list of projects, output JSON with the best matching project alias.

Available projects (alias -> name):
{project_list}

Output format: {{"alias": "<best_match_alias>", "confidence": 0.0-1.0}}
If no match, output: {{"alias": null, "confidence": 0.0}}"""


@dataclass
class ResolveResult:
    project_id: str | None = None
    project_name: str | None = None
    confidence: float = 0.0
    alternatives: list[dict] = field(default_factory=list)
    method: str = "none"


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


class ProjectResolver:
    def __init__(self, projects: dict[str, dict]) -> None:
        self._projects = projects
        self._lookup: dict[str, tuple[str, dict]] = {}
        for alias, info in projects.items():
            norm_alias = _normalize(alias)
            self._lookup[norm_alias] = (alias, info)
            norm_name = _normalize(info.get("name", ""))
            if norm_name and norm_name != norm_alias:
                self._lookup[norm_name] = (alias, info)
            # Also index the Plane identifier (e.g., "TOM", "ACME")
            norm_ident = _normalize(info.get("identifier", ""))
            if norm_ident and norm_ident not in self._lookup:
                self._lookup[norm_ident] = (alias, info)

    def resolve(self, spoken_name: str) -> ResolveResult:
        if not spoken_name or not self._projects:
            return ResolveResult()

        norm = _normalize(spoken_name)
        if not norm:
            return ResolveResult()

        # Tier 1a: Exact alias or name match
        if norm in self._lookup:
            alias, info = self._lookup[norm]
            return ResolveResult(
                project_id=info["id"],
                project_name=info.get("name", alias),
                confidence=1.0,
                method="exact",
            )

        # Tier 1b: Substring match (spoken name is part of a project name)
        substring_matches = []
        for key, (alias, info) in self._lookup.items():
            if norm in key or key in norm:
                substring_matches.append((alias, info, 0.85))

        if len(substring_matches) == 1:
            alias, info, conf = substring_matches[0]
            return ResolveResult(
                project_id=info["id"],
                project_name=info.get("name", alias),
                confidence=conf,
                method="substring",
            )

        # Tier 1c: Fuzzy match (SequenceMatcher)
        scores: list[tuple[float, str, dict]] = []
        for key, (alias, info) in self._lookup.items():
            ratio = SequenceMatcher(None, norm, key).ratio()
            if ratio >= FUZZY_THRESHOLD:
                scores.append((ratio, alias, info))

        scores.sort(key=lambda x: x[0], reverse=True)

        if scores:
            best_score, best_alias, best_info = scores[0]
            # Check if there's ambiguity (top 2 scores very close)
            if len(scores) > 1 and scores[1][0] > best_score - 0.1:
                # Ambiguous — return alternatives
                alts = [
                    {"alias": a, "name": i.get("name", a), "id": i["id"], "score": s}
                    for s, a, i in scores[:3]
                ]
                return ResolveResult(
                    confidence=best_score,
                    alternatives=alts,
                    method="fuzzy_ambiguous",
                )
            return ResolveResult(
                project_id=best_info["id"],
                project_name=best_info.get("name", best_alias),
                confidence=best_score,
                method="fuzzy",
            )

        # No match
        return ResolveResult()

    async def resolve_with_ai(
        self, spoken_name: str, transcript_context: str = ""
    ) -> ResolveResult:
        if not self._projects:
            return ResolveResult()

        project_list = "\n".join(
            f"  {alias} -> {info.get('name', alias)}"
            for alias, info in self._projects.items()
        )
        prompt = f"Spoken name: '{spoken_name}'"
        if transcript_context:
            prompt += f"\nFull transcript: '{transcript_context}'"

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(
                    OLLAMA_URL,
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "system": SYSTEM_PROMPT.format(project_list=project_list),
                        "stream": False,
                        "format": "json",
                    },
                )
                if resp.status_code != 200:
                    return ResolveResult()

                import json

                body = resp.json()
                raw = body.get("response", "")
                parsed = json.loads(raw)
                ai_alias = parsed.get("alias")
                ai_confidence = float(parsed.get("confidence", 0.0))

                if ai_alias and ai_alias in self._projects and ai_confidence > 0.5:
                    info = self._projects[ai_alias]
                    return ResolveResult(
                        project_id=info["id"],
                        project_name=info.get("name", ai_alias),
                        confidence=ai_confidence,
                        method="ai",
                    )
        except (httpx.ConnectError, httpx.TimeoutException, Exception):
            pass

        return ResolveResult()
