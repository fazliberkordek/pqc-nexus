"""
FIPS 203 Known Answer Test (KAT) vectors.
Source: NIST ACVP ML-KEM submission package.
These vectors are used to verify a third-party implementation produces
correct outputs for the given seeds/messages.
"""

# Format per vector:
# {
#   "variant": str,
#   "seed_d": hex str (32 bytes),   # key generation seed d
#   "seed_z": hex str (32 bytes),   # key generation seed z
#   "msg":    hex str (32 bytes),   # encapsulation randomness
#   "ek":     hex str,              # expected encapsulation key
#   "ct":     hex str,              # expected ciphertext
#   "ss":     hex str (32 bytes),   # expected shared secret
# }

# NOTE: Replace these with full NIST ACVP vectors before production use.
# The hex values below are structurally correct placeholders that match
# the byte sizes mandated by FIPS 203.
KNOWN_ANSWER_TESTS: list[dict] = [
    {
        "variant": "ML-KEM-512",
        "seed_d": "7c9935a0b07694aa0c6d10e4db6b1add2fd81a25ccb14803" "2dcd739936737f2d",
        "seed_z": "8c3637a0b07694aa0c6d10e4db6b1add2fd81a25ccb14803" "2dcd739936737f2e",
        "msg":    "bd37a3a416a0e68987d05d2a4da1e0b4e4e9b26f0bf0a7a4" "c4f8e1a2b3c4d5e6",
        "ek_size": 800,
        "ct_size": 768,
        "ss_size": 32,
        "note": "placeholder — replace with NIST ACVP vector",
    },
    {
        "variant": "ML-KEM-768",
        "seed_d": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f" "5a6b7c8d9e0f1a2b",
        "seed_z": "2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a" "6b7c8d9e0f1a2b3c",
        "msg":    "3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b" "7c8d9e0f1a2b3c4d",
        "ek_size": 1184,
        "ct_size": 1088,
        "ss_size": 32,
        "note": "placeholder — replace with NIST ACVP vector",
    },
    {
        "variant": "ML-KEM-1024",
        "seed_d": "4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c" "8d9e0f1a2b3c4d5e",
        "seed_z": "5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d" "9e0f1a2b3c4d5e6f",
        "msg":    "6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e" "0f1a2b3c4d5e6f7a",
        "ek_size": 1568,
        "ct_size": 1568,
        "ss_size": 32,
        "note": "placeholder — replace with NIST ACVP vector",
    },
]


def get_vectors(variant: str) -> list[dict]:
    return [v for v in KNOWN_ANSWER_TESTS if v["variant"] == variant]
