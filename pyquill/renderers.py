"""
Dataclasses to encapsulate rendering information for gates etc.
"""

from dataclasses import dataclass
from fractions import Fraction

import numpy as np


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


def gate_name_to_typst(name: str) -> str:
    """
    Converts a gate name (as defined by qiskit) to a typst string. The name
    must be a
    [`DAGOpNode`](https://docs.quantum.ibm.com/api/qiskit/qiskit.dagcircuit.DAGOpNode)
    opcode.
    """
    if len(name) == 1:
        return "$" + name.upper() + "$"
    raise NotImplementedError(f"Unsupported gate name: {name}")


@dataclass
class Renderer:
    """Abstract renderer"""

    def to_typst(self) -> str:
        """Renders the element to typst"""
        raise NotImplementedError()


@dataclass
class ControlledGate(Renderer):
    """A gate controlled by another wire"""

    name: str

    width: int
    """See `Gate.width`"""

    # controller: int
    # """Index of the controlling wire *relative* to the current wire"""

    def to_typst(self) -> str:
        t = gate_name_to_typst(self.name)
        return f"mqgate({t}, n: {self.width})"
        # return f"mqgate({t}, n: {self.width}, target: {self.controller})"


@dataclass
class ControlledPhaseGate(Renderer):
    """Represent the control of a phase gate"""

    target: int
    """Target wire index RELATIVE to the current wire"""

    theta: float

    def to_typst(self) -> str:
        theta = as_fraction_of_pi(self.theta)
        return f"ctrl({self.target}, wire-label: ${theta}$)"


@dataclass
class Gate(Renderer):
    """A basic renderer for gates with one or more qubits"""

    name: str

    width: int
    """
    Number of wires the gate spans over. This is NOT the number of qubits the
    gate acts on. For example, if the gate has qubit 2 and 5 as inputs, the
    width is 5 - 2 + 1 = 4. In particular, a unary gate has width 1.
    """

    def to_typst(self) -> str:
        t = gate_name_to_typst(self.name)
        if self.width == 1:
            return t
        return f"mqgate({t}, n: {self.width})"


@dataclass
class GateController(Renderer):
    """
    Wire that controls another gate (represented as a black dot). A
    `GateController` is also responsible to draw and annotate the control
    vertical wire.
    """

    target: int
    """Target wire index RELATIVE to the current wire"""

    def to_typst(self) -> str:
        return f"ctrl({self.target})"
