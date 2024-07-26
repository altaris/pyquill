"""
Dataclasses to encapsulate rendering information for gates etc.
"""

import re
from fractions import Fraction

import numpy as np
from qiskit.circuit import Qubit
from qiskit.dagcircuit import DAGOpNode


def _min_qarg(
    node: DAGOpNode, qubits_abs_idx: dict[Qubit, int], offset: int = 0
) -> tuple[Qubit, int]:
    """
    Return the input qubit with the minimum absolute index, and said index. If
    `offset` is specified, only consider qargs starting from that index.
    """
    min_q, min_ai = node.qargs[offset], qubits_abs_idx[node.qargs[offset]]
    for q in node.qargs[offset:]:
        ai = qubits_abs_idx[q]
        if ai < min_ai:
            min_q, min_ai = q, ai
    return min_q, min_ai


def _n_wires(
    node: DAGOpNode, qubits_abs_idx: dict[Qubit, int], offset: int = 0
) -> int:
    """
    Return the width of the gate, i.e. the number of wires it spans over. If
    `offset` is specified, only consider qargs starting from that index.
    """
    iai = [qubits_abs_idx[q] for q in node.qargs[offset:]]
    return max(iai) - min(iai) + 1


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


def easy_op_to_typst(op_name: str, parameters: list) -> str:
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
    if typst := easy_gates.get(op_name):
        if op_name == "rv":
            return typst.format(*parameters)
        return typst.format(*map(as_fraction_of_pi, parameters))
    return '"???"'


def render_opnode(
    node: DAGOpNode, qubits_abs_idx: dict[Qubit, int]
) -> dict[Qubit, str]:
    """
    Given an opnode and a mapping of qubits to their absolute indices, returns
    a dict that maps the input qubits of that node to a typst instruction that
    should be put to that qubit's wire.

    Args:
        node (DAGOpNode):
        qubits_abs_idx (dict[Qubit, int]): Mapping of qubits to their
            absolute indices.

    Returns:
        dict[Qubit, str]:
    """
    result: dict[Qubit, str] = {}

    if node.name == "cz":
        q0, q1 = node.qargs[:2]
        ri = qubits_abs_idx[q1] - qubits_abs_idx[q0]
        result[q0], result[q1] = f"ctrl({ri})", "ctrl(0)"

    elif node.name == "cp":
        q0, q1 = node.qargs[:2]
        ri = qubits_abs_idx[q1] - qubits_abs_idx[q0]
        theta = as_fraction_of_pi(node.op.params[0])
        result[q0] = f"ctrl({ri}, wire-label: ${theta}$)"
        result[q1] = "ctrl(0)"

    elif node.name == "p":
        theta = as_fraction_of_pi(node.op.params[0])
        result[node.qargs[0]] = f"phase(${theta}$)"

    elif node.name == "rzz":
        q0, q1 = node.qargs[:2]
        ri = qubits_abs_idx[q1] - qubits_abs_idx[q0]
        theta = as_fraction_of_pi(node.op.params[0])
        result[q0] = f"ctrl({ri}, wire-label: $Z Z ({theta})$)"
        result[q1] = "ctrl(0)"

    elif node.name == "swap":
        q0, q1 = node.qargs[:2]
        ri = qubits_abs_idx[q1] - qubits_abs_idx[q0]
        result[q0], result[q1] = f"swap({ri})", "targX()"

    elif node.name.startswith("c"):  # controlled gate
        if node.name.startswith("cc"):
            n_contols, gate = 2, node.name[2:]
        elif match := re.match(r"^c(\d+)(.*)$", node.name):
            n_contols, gate = int(match.group(1)), match.group(2)
        else:
            n_contols, gate = 1, node.name[1:]
        min_in_q, min_in_q_ai = _min_qarg(node, qubits_abs_idx, n_contols)
        n_wires = _n_wires(node, qubits_abs_idx, n_contols)
        for q_ctrl in node.qargs[:n_contols]:
            tgt = min_in_q_ai - qubits_abs_idx[q_ctrl]
            result[q_ctrl] = f"ctrl({tgt})"
        if gate == "swap":
            q1, q2 = node.qargs[n_contols : n_contols + 2]
            swp = qubits_abs_idx[q2] - qubits_abs_idx[q1]
            result[q1], result[q2] = f"swap({swp})", "targX()"
        elif gate == "x":
            result[node.qargs[-1]] = "targ()"
        else:
            tpst = easy_op_to_typst(gate, node.op.params)
            result[min_in_q] = f"mqgate({tpst}, n: {n_wires}, width: 5em)"

    else:  # Generic gate
        n_wires = _n_wires(node, qubits_abs_idx)
        tpst = easy_op_to_typst(node.name, node.op.params)
        min_qarg, min_qarg_ai = _min_qarg(node, qubits_abs_idx)
        if n_wires == 1:
            result[min_qarg] = tpst
        else:
            inputs = []
            for i, q in enumerate(node.qargs):
                j = qubits_abs_idx[q] - min_qarg_ai
                inputs.append(f'(qubit: {j}, label: "{i}")')
            clause = ", ".join(inputs)
            result[min_qarg] = (
                f"mqgate({tpst}, n: {n_wires}, inputs: ({clause}), width: 5em)"
            )

    return result
