"""Adapters: every external service touches JOE only through here.

Provider-specific code lives in this package and nowhere else. Capability
modules know nothing about COM, PowerShell, Windows, or any vendor.

  outlook_com       - live read-only Outlook via Windows COM
  voice_sapi        - Windows System.Speech synthesis and recognition
  research_provider - research provider selection (none bound in this build)
  reasoning_provider - the reasoning backend (none bound in this build)
  library_fs        - approved local filesystem Library sources
  dispatch_port     - the Dispatch boundary. Defined, deliberately unconnected.
"""

from .outlook_com import OutlookAdapterError, OutlookComAdapter, OutlookResult
from .voice_sapi import SapiVoiceAdapter, SpeechAttempt, VoiceAdapterError
from .research_provider import (
    ProviderResult,
    ResearchProviderAdapter,
    ResearchProviderError,
)
from .library_fs import LibraryFsAdapter, LibrarySourceStatus
from .m365_copilot import (
    CopilotApiError,
    CopilotReply,
    M365CopilotProvider,
    PREVIEW_NOTICE,
    PROVIDER_LABEL,
)
from .m365_copilot_auth import AuthState, CopilotAuth, DeviceFlow, msal_available
from .reasoning_provider import (
    Answer,
    ReasoningProvider,
    ReasoningProviderAdapter,
    ReasoningProviderError,
    ReasoningStatus,
)
from .dispatch_port import DispatchPort, DispatchPortError

__all__ = [
    "OutlookAdapterError", "OutlookComAdapter", "OutlookResult",
    "SapiVoiceAdapter", "SpeechAttempt", "VoiceAdapterError",
    "ProviderResult", "ResearchProviderAdapter", "ResearchProviderError",
    "LibraryFsAdapter", "LibrarySourceStatus",
    "CopilotApiError", "CopilotReply", "M365CopilotProvider",
    "PREVIEW_NOTICE", "PROVIDER_LABEL",
    "AuthState", "CopilotAuth", "DeviceFlow", "msal_available",
    "Answer", "ReasoningProvider", "ReasoningProviderAdapter",
    "ReasoningProviderError", "ReasoningStatus",
    "DispatchPort", "DispatchPortError",
]
