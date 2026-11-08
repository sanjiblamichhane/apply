"""
Language models behind one small interface (``LanguageModel``): local model servers speaking the ``native`` API or
the ``v1`` API, the switch between them (the choice in Settings → Model), finding them on this machine, and a fake
for tests.

    model = NativeModel(NativeConfig(base_url="http://localhost:11434", model="my-model"))
    reply = await model.chat("Write …", purpose=WRITING)
    data = await model.complete_json("Score …", schema)
"""

from .base import CHECK, GENERAL, SCORE, WRITING, LanguageModel, LLMError, ModelCheck, Reply
from .discover import DEFAULT_PORTS, Endpoint, FoundModel, discover, probe
from .fake import FakeModel
from .native import NativeConfig, NativeModel
from .switch import ModelChoice, SwitchableModel, client_for
from .v1 import V1Config, V1Model

__all__ = [
    "CHECK",
    "DEFAULT_PORTS",
    "GENERAL",
    "SCORE",
    "WRITING",
    "Endpoint",
    "FakeModel",
    "FoundModel",
    "LLMError",
    "LanguageModel",
    "ModelCheck",
    "ModelChoice",
    "NativeConfig",
    "NativeModel",
    "Reply",
    "SwitchableModel",
    "V1Config",
    "V1Model",
    "client_for",
    "discover",
    "probe",
]
