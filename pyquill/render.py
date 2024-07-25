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


def easy_node_to_typst(node: DAGOpNode) -> str:
    """
    Converts a gate name (as defined by qiskit) to a typst string. The name
    must be a
    [`DAGOpNode`](https://docs.quantum.ibm.com/api/qiskit/qiskit.dagcircuit.DAGOpNode)
    opcode.

    See also:
        https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.QuantumCircuit#methods-to-add-standard-instructions
    """
    easy_gates: dict[str, str] = {  # opname -> typst
        "dcx": '"DCX"',
        "ecr": '"ECR"',
        "h": "$H$",
        "id": "$I$",
        "iswap": '"iSWAP"',
        # "ms": '"GMS"',  # TODO:
        "p": "$P({0})$",
        # "pauli": "$$",
        # "prepare_state": "State Preparation",  # TODO:
        "r": "$R({0})$",
        # "rcccx": "$$",
        # "rccx": "$$",
        "rv": "$R_V ({0}, {1}, {2})$",
        "rx": "$R_X ({0})$",
        "rxx": "$R_(X X) ({0})$",
        "ry": "$R_Y ({0})$",
        "ryy": "$R_(Y Y) ({0})$",
        "rz": "$R_Z ({0})$",
        "rzx": "$R_(Z X) ({0})$",
        "s": "$S$",
        "sdg": "$S^dagger$",
        # "swap": "$$",
        "sx": "$sqrt(X)$",
        "sxdg": "$sqrt(X)^dagger$",
        "t": "$T$",
        "tdg": "$T^dagger$",
        "u": "$U({0}, {1}, {2})$",
        "u1": "$P({0})$",
        "u2": "$U(pi / 2, {0}, {1})$",
        "u3": "$U({0}, {1}, {2})$",
        "unitary": '"Unitary"',
        "x": "$X$",
        "y": "$Y$",
        "z": "$Z$",
    }
    if typst := easy_gates.get(node.name):
        if node.name == "rv":
            return typst.format(*node.op.params)
        return typst.format(*map(as_fraction_of_pi, node.op.params))
    return '"???"'


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

    elif node.name == "p":
        theta = as_fraction_of_pi(node.op.params[0])
        result[_q(0)] = f"phase(${theta}$)"

    elif node.name == "rzz":
        tgt, theta = _qai(1) - _qai(0), as_fraction_of_pi(node.op.params[0])
        result[_q(0)] = f"ctrl({tgt}, wire-label: $Z Z ({theta})$)"
        result[_q(1)] = "ctrl(0)"

    elif node.name == "swap":
        tgt = _qai(1) - _qai(0)
        result[_q(0)], result[_q(1)] = f"swap({tgt})", "targX()"

    elif node.name.startswith("cc"):  # two qubits controlled gate
        in_idx = [indices[q] for q in node.qargs[2:]]
        width = max(in_idx) - min(in_idx) + 1
        tgt_0, tgt_1 = _qai(2) - _qai(0), _qai(2) - _qai(1)
        name = node.name[2:].upper()
        result[_q(0)], result[_q(1)] = f"ctrl({tgt_0})", f"ctrl({tgt_1})"
        if name == "X":
            result[_q(2)] = "targ()"
        elif name == "Z":
            result[_q(2)] = "ctrl(0)"
        else:
            result[_q(2)] = f"mqgate(${name}$, n: {width})"

    elif node.name.startswith("c"):  # controlled gate
        in_idx = [indices[q] for q in node.qargs[1:]]
        width, tgt = max(in_idx) - min(in_idx) + 1, _qai(1) - _qai(0)
        name = node.name[1:].upper()
        result[_q(0)] = f"ctrl({tgt})"
        if name == "SWAP":
            swp = _qai(2) - _qai(1)
            result[_q(1)], result[_q(2)] = f"swap({swp})", "targX()"
        elif name == "X":
            result[_q(1)] = "targ()"
        else:
            result[_q(1)] = f"mqgate(${name}$, n: {width})"

    else:  # Generic gate
        in_idx = [indices[q] for q in node.qargs]
        width = max(in_idx) - min(in_idx) + 1
        name = easy_node_to_typst(node)
        result[_q(0)] = f"mqgate({name}, n: {width})"

    return result
