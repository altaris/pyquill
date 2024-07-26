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
    print("Unknown gate:", op_name)
    return '"???"'


def render_gate_box(
    node: DAGOpNode,
    qubits_abs_idx: dict[Qubit, int],
    n_controls: int = 0,
    op_name: str | None = None,
) -> str:
    """
    Renders a gate which can be represented as a box, e.g. `H` or `RXX`, but not
    `X`, `RZZ` or a phase gate.

    Args:
        node (DAGOpNode):
        qubits_abs_idx (dict[Qubit, int]):
        n_controls (int, optional):
        op_name (str | None, optional): To override the node's name.

    Returns:
        str:
    """
    n_wires = _n_wires(node, qubits_abs_idx, n_controls)
    tpst = easy_op_to_typst(op_name or node.name[n_controls:], node.op.params)
    if n_wires == 1:
        return tpst
    (_, min_qarg_ai), inputs = _min_qarg(node, qubits_abs_idx, n_controls), []
    for i, q in enumerate(node.qargs[n_controls:]):
        j = qubits_abs_idx[q] - min_qarg_ai
        inputs.append(f'(qubit: {j}, label: "{i}")')
    clause = ", ".join(inputs)
    return f"mqgate({tpst}, n: {n_wires}, inputs: ({clause}), width: 5em)"


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

    # Special cases
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

    # Controlled gate
    elif node.name.startswith("c") and len(node.qargs) >= 2:
        return render_opnode_crtl(node, qubits_abs_idx)

    # Generic gate
    else:
        min_qarg, _ = _min_qarg(node, qubits_abs_idx)
        result[min_qarg] = render_gate_box(node, qubits_abs_idx)

    return result


def render_opnode_crtl(
    node: DAGOpNode, qubits_abs_idx: dict[Qubit, int]
) -> dict[Qubit, str]:
    """
    Like `render_opnode`, but for controlled gates. The node's opname must start
    with a 'c'.

    Args:
        node (DAGOpNode):
        qubits_abs_idx (dict[Qubit, int]):

    Returns:
        dict[Qubit, str]:
    """
    if not node.name.startswith("c"):
        raise ValueError("This function is only accepts controlled gates.")

    # Determine the number of controls and the gate name
    if node.name.startswith("cc"):
        n_controls, op_name = 2, node.name[2:]
    elif match := re.match(r"^c(\d+)\w.*$", node.name):
        n_controls = int(match.group(1))
        op_name = node.name[len(str(n_controls)) + 1 :]
    else:
        n_controls, op_name = 1, node.name[1:]

    # Draw vertical line for all controls
    result = {}
    min_in_q, min_in_q_ai = _min_qarg(node, qubits_abs_idx, n_controls)
    for q_ctrl in node.qargs[:n_controls]:
        tgt = min_in_q_ai - qubits_abs_idx[q_ctrl]
        result[q_ctrl] = f"ctrl({tgt})"

    # Render controlled gate
    if op_name == "swap":
        q1, q2 = node.qargs[n_controls : n_controls + 2]
        swp = qubits_abs_idx[q2] - qubits_abs_idx[q1]
        result[q1], result[q2] = f"swap({swp})", "targX()"
    elif op_name == "x":
        result[node.qargs[-1]] = "targ()"
    else:
        result[min_in_q] = render_gate_box(
            node, qubits_abs_idx, n_controls, op_name
        )

    return result
