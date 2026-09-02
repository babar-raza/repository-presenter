"""Fail-closed startup check of the LLM gateway: discover and record its model catalog.

Extracted from the legacy ``preflight/llm_check.py``: the live ``GET /models`` and the rule that
an explicitly requested model absent from the live list is a hard failure are retained. Model
selection is removed: prompt manifests choose their route from the recorded catalog
(RESEARCH_AND_GUIDELINES.md section 18.4), so preflight never guesses a default and the catalog
is not queried again mid-job.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from repository_presenter.core.config import MODEL_VARIABLE, GatewayConfig
from repository_presenter.core.errors import GatewayError
from repository_presenter.core.llm.prompts import PromptRegistry, load_manifests, validate_routes
from repository_presenter.core.llm.transport import ModelCatalog, list_models

PREFLIGHT_DIRNAME = "preflight"
CATALOG_FILENAME = "catalog.json"


@dataclass(frozen=True)
class PreflightResult:
    catalog: ModelCatalog
    model_override: str | None
    prompts: PromptRegistry


def run_gateway_preflight(config: GatewayConfig, prompts_dir: Path) -> PreflightResult:
    """Reach the gateway, list its models, and check every governed route against the list.

    An override the catalog does not contain, and a manifest routed to a model the catalog no
    longer lists, both fail closed: no job runs on a guessed model.
    """
    prompts = load_manifests(prompts_dir)
    catalog = list_models(config)
    if config.model_override is not None and config.model_override not in catalog.ids:
        raise GatewayError(
            f"{MODEL_VARIABLE}={config.model_override!r} is not in the live model catalog "
            f"({', '.join(catalog.ids)})"
        )
    validate_routes(prompts, catalog.ids)
    return PreflightResult(catalog, config.model_override, prompts)


def write_catalog(result: PreflightResult, path: Path) -> str:
    """Record the discovered catalog and the routed manifests as deterministic JSON; SHA-256."""
    payload = {
        "schema_version": 1,
        "base_url": result.catalog.base_url,
        "models": [{"id": model.id, "owned_by": model.owned_by} for model in result.catalog.models],
        "model_override": result.model_override,
        "prompts": [
            {"prompt_id": job, "model_route": loaded.manifest.model_route, "sha256": loaded.sha256}
            for job, loaded in sorted(result.prompts.manifests.items())
        ],
    }
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
