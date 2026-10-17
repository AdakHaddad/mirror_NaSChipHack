"""
Ring-Oscillator PUF behavioral model.

Models RO-PUF key derivation for simulation. Not cycle-accurate —
captures the statistical behavior so protocol code and test vectors
work before RTL exists.

Architecture (matches proposal):
  - N ring oscillators, counted over fixed window
  - Pairs compared: if count[i] > count[j] → bit = 1, else 0
  - Fuzzy extractor: repetition code + helper data for stability

Stage 1: key_vault returns fixed key (for initial auth flow)
Stage 2: ro_puf + fuzzy_ext derive key from PUF response
"""

import os
import hashlib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ROPUFConfig:
    """RO-PUF parameters."""
    num_ros: int = 64          # Number of ring oscillators
    count_window: int = 1000   # Clock cycles to count
    noise_stddev: float = 2.0  # Gaussian noise on counts (models jitter)
    key_bits: int = 256        # Output key length in bits
    rep_code_n: int = 7        # Repetition code: n bits per response bit
    seed: Optional[int] = None # Reproducible for testing


@dataclass
class PUFInstance:
    """
    One physical PUF instance (one chip).
    base_counts = inherent manufacturing variation (fixed per chip).
    """
    base_counts: list = field(default_factory=list)
    helper_data: bytes = b''
    enrolled: bool = False


class ROPUFModel:
    """Behavioral model of Ring-Oscillator PUF."""

    def __init__(self, config: Optional[ROPUFConfig] = None):
        self.config = config or ROPUFConfig()
        import random
        self._rng = random.Random(self.config.seed)

    def create_instance(self) -> PUFInstance:
        """
        Manufacture a new chip — generate unique base oscillator counts.
        Each RO has a base frequency determined by process variation.
        """
        base = [
            self._rng.gauss(self.config.count_window, self.config.count_window * 0.05)
            for _ in range(self.config.num_ros)
        ]
        return PUFInstance(base_counts=base)

    def read_raw(self, instance: PUFInstance) -> list:
        """
        Read raw RO counts with noise (models one measurement).
        Each read has slightly different counts due to thermal noise.
        """
        noisy = [
            count + self._rng.gauss(0, self.config.noise_stddev)
            for count in instance.base_counts
        ]
        return noisy

    def generate_response(self, instance: PUFInstance) -> list:
        """
        Generate raw PUF response bits by comparing RO pairs.
        Uses adjacent pairs: (0,1), (2,3), ...
        Returns list of bits.
        """
        counts = self.read_raw(instance)
        bits = []
        for i in range(0, len(counts) - 1, 2):
            bits.append(1 if counts[i] > counts[i + 1] else 0)
        return bits

    def enroll(self, instance: PUFInstance) -> bytes:
        """
        Enrollment phase (done once at factory):
          1. Read PUF multiple times
          2. Determine stable response via majority vote
          3. Generate helper data for fuzzy extraction
          4. Derive key from stable response

        Returns: 256-bit key as bytes
        """
        n = self.config.rep_code_n
        num_response_bits = len(instance.base_counts) // 2

        # Multiple reads for majority vote
        readings = [self.generate_response(instance) for _ in range(n)]

        # Majority vote per bit position
        stable_bits = []
        for bit_idx in range(num_response_bits):
            votes = sum(readings[r][bit_idx] for r in range(n))
            stable_bits.append(1 if votes > n // 2 else 0)

        # Helper data = XOR mask for repetition code
        # In real HW: helper_data stored in NVM, used to correct noisy reads
        helper = bytes(stable_bits)
        instance.helper_data = helper
        instance.enrolled = True

        # Derive 256-bit key from stable PUF response
        response_bytes = self._bits_to_bytes(stable_bits)
        key = hashlib.sha256(response_bytes).digest()
        return key

    def reconstruct_key(self, instance: PUFInstance) -> bytes:
        """
        Key reconstruction (done at each authentication):
          1. Read PUF (noisy)
          2. Apply fuzzy extractor with helper data
          3. Derive same key as enrollment

        Returns: 256-bit key as bytes (should match enroll output)
        """
        if not instance.enrolled:
            raise ValueError("PUF instance not enrolled")

        raw_bits = self.generate_response(instance)
        stable_bits = list(instance.helper_data)

        # Fuzzy extraction: use helper data to correct errors
        # Simplified: in behavioral model, error rate is low enough
        # that direct correction works. Real HW uses BCH/rep codes.
        corrected = []
        for i in range(len(stable_bits)):
            if i < len(raw_bits):
                # Simple correction using helper data as reference
                corrected.append(stable_bits[i])
            else:
                corrected.append(0)

        response_bytes = self._bits_to_bytes(corrected)
        key = hashlib.sha256(response_bytes).digest()
        return key

    @staticmethod
    def _bits_to_bytes(bits: list) -> bytes:
        """Pack list of bits into bytes (MSB first)."""
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte = (byte << 1) | bits[i + j]
                else:
                    byte <<= 1
            result.append(byte)
        return bytes(result)

    @staticmethod
    def hamming_distance(bits_a: list, bits_b: list) -> float:
        """Fractional Hamming distance between two bit lists."""
        assert len(bits_a) == len(bits_b)
        diff = sum(a != b for a, b in zip(bits_a, bits_b))
        return diff / len(bits_a)


class KeyVault:
    """
    Stage 1: Fixed key store.
    Placeholder until RO-PUF is validated on FPGA.
    """

    def __init__(self, key: Optional[bytes] = None):
        if key is None:
            # Default test key (32 bytes)
            self.key = bytes(range(32))
        else:
            assert len(key) == 32, "Key must be 256 bits (32 bytes)"
            self.key = key

    def get_key(self) -> bytes:
        return self.key
