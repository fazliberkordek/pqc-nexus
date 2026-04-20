"""FIPS 203 ML-KEM parameter sets and byte-size constants."""
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class MLKEMParams:
    k: int             # lattice rank
    eta1: int          # noise param for key gen
    eta2: int          # noise param for encryption
    du: int            # ciphertext compression (u)
    dv: int            # ciphertext compression (v)
    ek_size: int       # encapsulation key size (bytes)
    dk_size: int       # decapsulation key size (bytes)
    ct_size: int       # ciphertext size (bytes)
    ss_size: int = 32  # shared secret always 32 bytes


PARAMS: dict[str, MLKEMParams] = {
    "ML-KEM-512": MLKEMParams(
        k=2, eta1=3, eta2=2, du=10, dv=4,
        ek_size=800, dk_size=1632, ct_size=768,
    ),
    "ML-KEM-768": MLKEMParams(
        k=3, eta1=2, eta2=2, du=10, dv=4,
        ek_size=1184, dk_size=2400, ct_size=1088,
    ),
    "ML-KEM-1024": MLKEMParams(
        k=4, eta1=2, eta2=2, du=11, dv=5,
        ek_size=1568, dk_size=3168, ct_size=1568,
    ),
}


class MLKEMVariant(str, Enum):
    KEM_512  = "ML-KEM-512"
    KEM_768  = "ML-KEM-768"
    KEM_1024 = "ML-KEM-1024"
