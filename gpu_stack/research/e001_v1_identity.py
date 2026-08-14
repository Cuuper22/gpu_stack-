"""Frozen SHA-256 identities for the published E001 v1 artifacts.

These hashes pin the v1 protocol, engine source, result artifacts, and
scenario exactly as published. They live outside :mod:`gpu_stack.research.e001`
on purpose: if the hashes sat next to the code they verify, recovery-v2 work
could change both together and a modified v1 would silently authorize itself.
Changing any value here must be an explicit v1 compatibility decision, never
a side effect of regenerating artifacts.
"""

E001_V1_FROZEN_PROTOCOL_SHA256 = (
    "cadd8fcb4ecdac66d20cabda11e6c73a82cbfc1f083d0fcee8fe4ebfca101a10"
)
E001_V1_FROZEN_ENGINE_SOURCE_SHA256 = (
    "bfabd89583050b518c718f0ca7034eb6994bab20476d434e71a873ac8f97e1b7"
)
E001_V1_FROZEN_RESULT_ARTIFACT_SHA256 = (
    "fa26aeb9dca512356f496502e0bcf5c2ea88ea4f2e2737a122bcafd64543f562"
)
E001_V1_FROZEN_OBSERVATORY_ARTIFACT_SHA256 = (
    "49a581a48293332ee46c315104ea9acf10444e0ed61a545ba496f0f96b12acbc"
)
E001_V1_FROZEN_SCENARIO_SHA256 = (
    "532fad5cf7698cc9f7f81090519f020374f43f059a4c0d67d59acd65d26b9e0d"
)
E001_V1_RESULT_RELATIVE_PATH = (
    "experiments/e001-beyond-one-datacenter/results/screening-mechanics-v1.json"
)
E001_V1_OBSERVATORY_RELATIVE_PATH = "docs/data/e001-screening-v1.json"


__all__ = [
    "E001_V1_FROZEN_ENGINE_SOURCE_SHA256",
    "E001_V1_FROZEN_OBSERVATORY_ARTIFACT_SHA256",
    "E001_V1_FROZEN_PROTOCOL_SHA256",
    "E001_V1_FROZEN_RESULT_ARTIFACT_SHA256",
    "E001_V1_FROZEN_SCENARIO_SHA256",
    "E001_V1_OBSERVATORY_RELATIVE_PATH",
    "E001_V1_RESULT_RELATIVE_PATH",
]
