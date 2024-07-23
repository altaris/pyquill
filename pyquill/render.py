"""
Dataclasses to encapsulate rendering information for gates etc.
"""

from fractions import Fraction

import numpy as np
from qiskit.circuit import Qubit
from qiskit.dagcircuit import DAGOpNode


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


def render_opnode(
    node: DAGOpNode, indices: dict[Qubit, int]
) -> dict[Qubit, str]:
    """
    Given an opnode and a mapping of qubits to their absolute indices, returns
    a dict that maps the input qubits of that node to a typst instruction that
    should be put to that qubit's wire.

    Args:
        node (DAGOpNode):
        indices (dict[Qubit, int]):

    Returns:
        dict[Qubit, str]:
    """

    def _q(qarg_idx: int) -> Qubit:
        """Node's input qubit at the given index"""
        return node.qargs[qarg_idx]

    def _qai(qarg_idx: int) -> int:
        """Converts a node's qarg index to an absolute index"""
        return indices[node.qargs[qarg_idx]]

    result: dict[Qubit, str] = {}

    if node.name == "cz":
        tgt = _qai(1) - _qai(0)
        result[_q(0)], result[_q(1)] = f"ctrl({tgt})", "ctrl(0)"

    elif node.name == "cp":
        tgt, theta = _qai(1) - _qai(0), as_fraction_of_pi(node.op.params[0])
        result[_q(0)] = f"ctrl({tgt}, wire-label: ${theta}$)"
        result[_q(1)] = "ctrl(0)"

    elif node.name.startswith("cc"):  # two qubits controlled gate
        in_idx = [indices[q] for q in node.qargs[2:]]
        width = max(in_idx) - min(in_idx) + 1
        tgt_0, tgt_1 = _qai(2) - _qai(0), _qai(2) - _qai(1)
        name = node.name[2:].upper()
        result[_q(0)], result[_q(1)] = f"ctrl({tgt_0})", f"ctrl({tgt_1})"
        if name == "Z":
            result[_q(2)] = "ctrl(0)"
        else:
            result[_q(2)] = f"mqgate(${name}$, n: {width})"

    elif node.name.startswith("c"):  # controlled gate
        in_idx = [indices[q] for q in node.qargs[1:]]
        width, tgt = max(in_idx) - min(in_idx) + 1, _qai(1) - _qai(0)
        name = node.name[1:].upper()
        result[_q(0)] = f"ctrl({tgt})"
        result[_q(1)] = f"mqgate(${name}$, n: {width})"

    else:  # Generic gate
        in_idx = [indices[q] for q in node.qargs]
        width = max(in_idx) - min(in_idx) + 1
        name = node.name.upper()
        result[_q(0)] = f"mqgate(${name}$, n: {width})"
    return result
