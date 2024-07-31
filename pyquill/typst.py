"""Utilities to generate typst code"""

from fractions import Fraction

import numpy as np
from qiskit import QuantumRegister
from qiskit.circuit import Register

SUPPORTED_TYPST_SYMBOLS = [
    "alpha",
    "Alpha",
    "beta",
    "Beta",
    "chi",
    "Chi",
    "delta",
    "Delta",
    "epsilon",
    "Epsilon",
    "eta",
    "Eta",
    "gamma",
    "Gamma",
    "iota",
    "Iota",
    "kai",
    "Kai",
    "kappa",
    "Kappa",
    "lambda",
    "Lambda",
    "mu",
    "Mu",
    "nu",
    "Nu",
    "omega",
    "Omega",
    "omicron",
    "Omicron",
    "phi",
    "Phi",
    "pi",
    "Pi",
    "psi",
    "Psi",
    "rho",
    "Rho",
    "sigma",
    "Sigma",
    "tau",
    "Tau",
    "theta",
    "Theta",
    "upsilon",
    "Upsilon",
    "xi",
    "Xi",
    "zeta",
    "Zeta",
]


# pylint: disable=too-many-return-statements
def as_fraction_of_pi(theta: float) -> str:
    """
    Represents a float as an integer fraction of pi, as a typst math string.
    """
    if theta == 0:
        return "0"
    fraction = Fraction(theta / np.pi).limit_denominator()
    n, d = fraction.numerator, fraction.denominator
    if n == 1:
        if d == 1:
            return "pi"
        return f"pi / {d}"
    if n == -1:
        if d == 1:
            return "-pi"
        return f"-pi / {d}"
    if d == 1:
        return f"{n} pi"
    if d == -1:
        return f"-{n} pi"
    return f"({n} pi) / {d}"


# pylint: disable=protected-access
def wire_name(register: Register, index: int | None = None) -> str:
    """
    Creates a wire name (the labels on the very left of a wire in a quantum
    circuit diagram) from a register (quantum or classical) and an index.
    """
    if len(register._name) == 1 or register._name in SUPPORTED_TYPST_SYMBOLS:
        name = register._name
    else:
        name = f'"{register._name}"'
    if index is not None and register.size > 1:
        name = f"{name}_({index})"
    if isinstance(register, QuantumRegister):
        name = f"ket({name})"
    return f"${name}$"
