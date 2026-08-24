"""Lineage helpers for agent-version history.

"Training" means publishing a new child version into append-only history and
comparing verified evidence across matches. It never means mutating ranked
history, and a child version existing says nothing about whether the agent
improved. These helpers only establish that a parent/child edge is well-formed
and stays inside one key.
"""

from .passport import PassportError, verify_passport


class LineageError(ValueError):
    """A claimed lineage edge is malformed or crosses keys."""


def _verified(passport):
    try:
        return verify_passport(passport)
    except PassportError as e:
        raise LineageError(f"lineage requires a valid passport: {e}") from e


def lineage_edge(parent_passport, child_passport):
    """Return the verified parent->child edge, or raise LineageError."""
    parent = _verified(parent_passport)
    child = _verified(child_passport)
    if child["parentVersionId"] is None:
        raise LineageError("child declares no parentVersionId")
    if child["parentVersionId"] != parent["versionId"]:
        raise LineageError("child parentVersionId does not name the parent versionId")
    if child["agentId"] != parent["agentId"]:
        raise LineageError(
            "cross-key parent lineage refused: parent and child bind different public keys"
        )
    return {
        "parentVersionId": parent["versionId"],
        "childVersionId": child["versionId"],
        "agentId": parent["agentId"],
    }


def require_same_key_lineage(versions_by_id):
    """Validate every declared parent edge present in the corpus.

    `versions_by_id` maps versionId -> verified normalized passport dict. A
    parent missing from the corpus is not an error (history may predate the
    corpus); a present parent bound to a *different* key is.
    """
    edges = []
    for version_id in sorted(versions_by_id):
        child = versions_by_id[version_id]
        parent_id = child.get("parentVersionId")
        if not parent_id:
            continue
        parent = versions_by_id.get(parent_id)
        if parent is None:
            continue
        if parent["agentId"] != child["agentId"]:
            raise LineageError(
                "cross-key parent lineage refused: "
                f"{parent_id} and {version_id} claim the same lineage under different keys"
            )
        edges.append(
            {
                "parentVersionId": parent_id,
                "childVersionId": version_id,
                "agentId": child["agentId"],
            }
        )
    return edges


__all__ = ["LineageError", "lineage_edge", "require_same_key_lineage"]
