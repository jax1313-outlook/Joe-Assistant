"""JOE application core.

  bootstrap - makes the six packaged components importable
  config    - configuration and path containment
  logbook   - plain-text event log
  router    - ordinary language to a bounded capability
  service   - AssistantService, the core the UI renders

Governing doctrine: JOE_CONSTITUTION_v1
"""

__version__ = "1.0.0"

from . import bootstrap  # noqa: F401  - must run before component imports
from .config import Config, ConfigError, ContainmentError, assert_within_plugin
from .logbook import Logbook
from .router import Route, route, wants_driver_mode
from .service import AssistantService, Interaction

__all__ = [
    "__version__",
    "Config", "ConfigError", "ContainmentError", "assert_within_plugin",
    "Logbook", "Route", "route", "wants_driver_mode",
    "AssistantService", "Interaction",
]
