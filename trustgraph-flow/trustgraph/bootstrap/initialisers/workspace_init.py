"""
WorkspaceInit initialiser — creates a workspace and populates it from
either the ``__template__`` workspace or a seed file on disk.

Parameters
----------
workspace : str
    Target workspace to create / populate.
source : str
    Either ``"template"`` (copy the full contents of the
    ``__template__`` workspace) or ``"seed-file"`` (read from
    ``seed_file``).
seed_file : str (required when source=="seed-file")
    Path to a JSON seed file with the same shape TemplateSeed consumes.
overwrite : bool (default False)
    On re-run (flag change), if True overwrite all keys; if False,
    upsert-missing-only (preserves in-workspace customisations).

Raises (in ``run``)
-------------------
When source is ``"template"``, raises ``RuntimeError`` if the
``__template__`` workspace is empty — indicating that TemplateSeed
hasn't run yet.  The bootstrapper's retry loop will re-attempt on
the next cycle once the prerequisite is satisfied.
"""

import json

from .. base import Initialiser

TEMPLATE_WORKSPACE = "__template__"


class WorkspaceInit(Initialiser):

    def __init__(
            self,
            workspace="default",
            source="template",
            seed_file=None,
            overwrite=False,
            **kwargs,
    ):
        super().__init__(**kwargs)

        if source not in ("template", "seed-file"):
            raise ValueError(
                f"WorkspaceInit: source must be 'template' or "
                f"'seed-file', got {source!r}"
            )
        if source == "seed-file" and not seed_file:
            raise ValueError(
                "WorkspaceInit: seed_file required when source='seed-file'"
            )

        self.workspace = workspace
        self.source = source
        self.seed_file = seed_file
        self.overwrite = overwrite

    async def run(self, ctx, old_flag, new_flag):
        if self.source == "seed-file":
            tree = self._load_seed_file()
        else:
            tree = await self._load_from_template(ctx)

        if old_flag is None or self.overwrite:
            await self._write_all(ctx, tree)
        else:
            await self._upsert_missing(ctx, tree)

    def _load_seed_file(self):
        with open(self.seed_file) as f:
            return json.load(f)

    async def _load_from_template(self, ctx):
        """Build a seed tree from the entire ``__template__`` workspace.
        Raises if the workspace is empty, so the bootstrapper knows
        the prerequisite isn't met yet."""

        raw_tree = await ctx.config.get_all(TEMPLATE_WORKSPACE)

        tree = {}
        total = 0
        for type_name, entries in raw_tree.items():
            parsed = {}
            for key, raw in entries.items():
                if raw is None:
                    continue
                try:
                    parsed[key] = json.loads(raw)
                except Exception:
                    parsed[key] = raw
                total += 1
            if parsed:
                tree[type_name] = parsed

        if total == 0:
            raise RuntimeError(
                "Template workspace is empty — has TemplateSeed run yet?"
            )

        ctx.logger.debug(
            f"Loaded {total} template entries across {len(tree)} types"
        )
        return tree

    async def _write_all(self, ctx, tree):
        values = []
        for type_name, entries in tree.items():
            for key, value in entries.items():
                values.append((type_name, key, json.dumps(value)))
        if values:
            await ctx.config.put_many(self.workspace, values)
        ctx.logger.info(
            f"Workspace {self.workspace!r} populated with "
            f"{len(values)} entries"
        )

    async def _upsert_missing(self, ctx, tree):
        written = 0
        for type_name, entries in tree.items():
            existing = set(
                await ctx.config.keys(self.workspace, type_name)
            )
            values = []
            for key, value in entries.items():
                if key not in existing:
                    values.append(
                        (type_name, key, json.dumps(value))
                    )
            if values:
                await ctx.config.put_many(self.workspace, values)
                written += len(values)
        ctx.logger.info(
            f"Workspace {self.workspace!r} upsert-missing: "
            f"{written} new entries"
        )
