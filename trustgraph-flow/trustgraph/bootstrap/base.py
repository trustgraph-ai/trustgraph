"""
Bootstrap framework: Initialiser base class and per-wake context.

See docs/tech-specs/bootstrap.md for the full design.
"""

import logging
from dataclasses import dataclass
from typing import Any


@dataclass
class InitContext:
    """Shared per-wake context passed to each initialiser.

    The bootstrapper constructs one of these on every wake cycle,
    tears it down at cycle end, and passes it into each initialiser's
    ``run()`` method.  Fields are short-lived and safe to use during
    a single cycle only.
    """

    logger: logging.Logger
    config: Any    # ConfigClient
    make_flow_client: Any  # callable(workspace) -> RequestResponse


class Initialiser:
    """Base class for bootstrap initialisers.

    Subclasses implement :meth:`run`.  The bootstrapper manages
    completion state, flag comparison, retry and error handling —
    subclasses describe only the work to perform.

    Class attributes:

    * ``wait_for_services`` (bool, default ``True``): when ``True`` the
      initialiser only runs after the bootstrapper's service gate has
      passed (config-svc and flow-svc reachable).  Set ``False`` for
      initialisers that bring up infrastructure the gate itself
      depends on — principally Pulsar topology, without which
      config-svc cannot come online.
    """

    wait_for_services: bool = True

    def __init__(self, **params):
        # Subclasses should consume their own params via keyword
        # arguments in their own __init__ signatures.  This catch-all
        # is here so any kwargs that filter through unnoticed don't
        # raise TypeError on construction.
        pass

    async def run(self, ctx, old_flag, new_flag):
        """Perform initialisation work.

        :param ctx: :class:`InitContext` with logger, config client,
            flow-svc client.
        :param old_flag: Previously-stored flag string, or ``None`` if
            this initialiser has never successfully completed in this
            deployment.
        :param new_flag: Currently-configured flag.  A string chosen
            by the operator; typically something like ``"v1"``.

        :raises: Any exception on failure.  The bootstrapper catches,
            logs, and re-runs on the next cycle; completion state is
            only written on clean return.
        """
        raise NotImplementedError
