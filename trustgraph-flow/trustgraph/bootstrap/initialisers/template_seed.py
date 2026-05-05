"""
TemplateSeed initialiser — populates the reserved ``__template__``
workspace from an external JSON seed file.

Seed file shape:

.. code-block:: json

    {
        "flow-blueprint": {
            "ontology": { ... },
            "agent":    { ... }
        },
        "prompt": {
            ...
        },
        ...
    }

Top-level keys are config types; nested keys are config entries.
Values are arbitrary JSON (they'll be ``json.dumps()``'d on write).

Parameters
----------
config_file : str
    Path to the seed file on disk.
overwrite : bool (default False)
    On re-run (flag change), if True overwrite all keys; if False
    upsert-missing-only (preserves any operator customisation of
    the template).
"""

import json

from .. base import Initialiser

TEMPLATE_WORKSPACE = "__template__"


class TemplateSeed(Initialiser):

    def __init__(self, config_file, overwrite=False, **kwargs):
        super().__init__(**kwargs)
        if not config_file:
            raise ValueError("TemplateSeed requires 'config_file'")
        self.config_file = config_file
        self.overwrite = overwrite

    async def run(self, ctx, old_flag, new_flag):

        with open(self.config_file) as f:
            seed = json.load(f)

        if old_flag is None:
            # Clean first run — write every entry.
            await self._write_all(ctx, seed)
            return

        # Re-run after flag change.
        if self.overwrite:
            await self._write_all(ctx, seed)
        else:
            await self._upsert_missing(ctx, seed)

    async def _write_all(self, ctx, seed):
        values = []
        for type_name, entries in seed.items():
            for key, value in entries.items():
                values.append((type_name, key, json.dumps(value)))
        if values:
            await ctx.config.put_many(TEMPLATE_WORKSPACE, values)
        ctx.logger.info(
            f"Template seeded with {len(values)} entries"
        )

    async def _upsert_missing(self, ctx, seed):
        written = 0
        for type_name, entries in seed.items():
            existing = set(
                await ctx.config.keys(TEMPLATE_WORKSPACE, type_name)
            )
            values = []
            for key, value in entries.items():
                if key not in existing:
                    values.append(
                        (type_name, key, json.dumps(value))
                    )
            if values:
                await ctx.config.put_many(TEMPLATE_WORKSPACE, values)
                written += len(values)
        ctx.logger.info(
            f"Template upsert-missing: {written} new entries"
        )
