"""
Dataclasses to encapsulate rendering information for gates etc.
"""

import re

from qiskit.circuit import Bit, Qubit
from qiskit.dagcircuit import DAGOpNode

from .typst import as_fraction_of_pi


def _min_qarg(
    node: DAGOpNode, bits_abs_idx: dict[Bit, int], qargs_offset: int = 0
) -> tuple[Qubit, int]:
    """
    Return the input qubit with the minimum absolute index, and said index. If
    `qargs_offset` is specified, only consider qargs starting from that index.
    """
    min_q = node.qargs[qargs_offset]
    min_ai = bits_abs_idx[node.qargs[qargs_offset]]
    for q in node.qargs[qargs_offset:]:
        ai = bits_abs_idx[q]
        if ai < min_ai:
            min_q, min_ai = q, ai
    return min_q, min_ai


def _n_wires(
    node: DAGOpNode, bits_abs_idx: dict[Bit, int], qargs_offset: int = 0
) -> int:
    """
    Return the width of the gate, i.e. the number of wires it spans over. If
    `qargs_offset` is specified, only consider qargs starting from that index.
    """
    iai = [bits_abs_idx[q] for q in node.qargs[qargs_offset:]]
    return max(iai) - min(iai) + 1


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
        "p": "$P({0})$",
        "r": "$R({0})$",
        "rv": "$R_V ({0}, {1}, {2})$",
        "rx": "$R_X ({0})$",
        "rxx": "$R_(X X) ({0})$",
        "ry": "$R_Y ({0})$",
        "ryy": "$R_(Y Y) ({0})$",
        "rz": "$R_Z ({0})$",
        "rzx": "$R_(Z X) ({0})$",
        "s": "$S$",
        "sdg": "$S^dagger$",
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
        # "ms": '"GMS"',  # TODO:
        # "pauli": "$$", # TODO: maybe?
        # "prepare_state": "State Preparation",  # TODO:
        # "rcccx": "$$",
        # "rccx": "$$",
    }
    if typst := easy_gates.get(op_name):
        if op_name == "rv":
            return typst.format(*parameters)
        return typst.format(*map(as_fraction_of_pi, parameters))
    return '"???"'


def render_gate_box(
    node: DAGOpNode,
    bits_abs_idx: dict[Bit, int],
    n_controls: int = 0,
    op_name: str | None = None,
) -> str:
    """
    Renders a gate which can be represented as a box, e.g. `H` or `RXX`, but not
    `X`, `RZZ` or a phase gate.

    Args:
        node (DAGOpNode):
        bits_abs_idx (dict[Qubit, int]):
        n_controls (int, optional):
        op_name (str | None, optional): To override the node's name.

    Returns:
        str:
    """
    n_wires = _n_wires(node, bits_abs_idx, n_controls)
    tpst = easy_op_to_typst(op_name or node.name[n_controls:], node.op.params)
    if n_wires == 1:
        return tpst
    (_, min_qarg_ai), inputs = _min_qarg(node, bits_abs_idx, n_controls), []
    for i, q in enumerate(node.qargs[n_controls:]):
        j = bits_abs_idx[q] - min_qarg_ai
        inputs.append(f'(qubit: {j}, label: "{i}")')
    clause = ", ".join(inputs)
    return f"mqgate({tpst}, n: {n_wires}, inputs: ({clause}), width: 5em)"


def render_opnode(
    node: DAGOpNode,
    bits_abs_idx: dict[Bit, int],
    qargs_offset: int = 0,
    op_name: str | None = None,
) -> dict[Bit, str]:
    """
    Given an opnode and a mapping of qubits to their absolute indices, returns
    a dict that maps the input qubits of that node to a typst instruction that
    should be put to that qubit's wire.

    Args:
        node (DAGOpNode):
        bits_abs_idx (dict[Qubit, int]): Mapping of bits (quantum and classical)
            to their absolute wire indices.
        qargs_offset (int, optional): If set, the first `qargs_offset` qargs
            are ignored.
        op_name (str | None, optional): To override the node's name.

    Returns:
        dict[Bit, str]:
    """
    op_name, qargs = op_name or node.name, node.qargs[qargs_offset:]
    result: dict[Bit, str] = {}

    # Special cases
    if op_name == "barrier":
        result[qargs[0]] = (
            f'slice(n: {len(qargs)}, stroke: (paint: black, dash: "dashed"))'
        )
        for q in bits_abs_idx:
            if q != qargs[0]:
                result[q] = "0"
    elif op_name == "cp":
        q0, q1 = qargs[:2]
        ri = bits_abs_idx[q1] - bits_abs_idx[q0]
        theta = as_fraction_of_pi(node.op.params[0])
        result[q0] = f"ctrl({ri}, wire-label: ${theta}$)"
        result[q1] = "ctrl(0)"
    elif op_name == "cz":
        q0, q1 = qargs[:2]
        ri = bits_abs_idx[q1] - bits_abs_idx[q0]
        result[q0], result[q1] = f"ctrl({ri})", "ctrl(0)"
    elif op_name == "measure":
        q0, c0 = qargs[0], node.cargs[0]
        ri = bits_abs_idx[c0] - bits_abs_idx[q0]
        result[q0], result[c0] = f"meter(target: {ri})", "ctrl(0)"
        # result[c0] = f"ctrl(0, label: ((content: ${c0._index}$, pos: bottom)))"
    elif op_name == "p":
        theta = as_fraction_of_pi(node.op.params[0])
        result[qargs[0]] = f"phase(${theta}$)"
    elif op_name == "rzz":
        q0, q1 = qargs[:2]
        ri = bits_abs_idx[q1] - bits_abs_idx[q0]
        theta = as_fraction_of_pi(node.op.params[0])
        result[q0] = f"ctrl({ri}, wire-label: $Z Z ({theta})$)"
        result[q1] = "ctrl(0)"
    elif op_name == "swap":
        q0, q1 = qargs[:2]
        ri = bits_abs_idx[q1] - bits_abs_idx[q0]
        result[q0], result[q1] = f"swap({ri})", "targX()"
    elif op_name == "x" and node.op.name.endswith("cx"):
        result[qargs[0]] = "targ()"

    # Controlled gate
    elif op_name.startswith("c") and len(qargs) >= 2:
        # TODO: make a recursive call to render_opnode instead?
        return render_opnode_crtl(node=node, bits_abs_idx=bits_abs_idx)

    # Generic (boxed) gate
    else:
        min_qarg, _ = _min_qarg(node, bits_abs_idx, qargs_offset)
        result[min_qarg] = render_gate_box(
            node=node,
            bits_abs_idx=bits_abs_idx,
            n_controls=qargs_offset,
            op_name=op_name,
        )

    return result


def render_opnode_crtl(
    node: DAGOpNode, bits_abs_idx: dict[Bit, int]
) -> dict[Bit, str]:
    """
    Like `render_opnode`, but for controlled gates. The node's opname must start
    with a 'c'.

    Args:
        node (DAGOpNode):
        bits_abs_idx (dict[Bit, int]):

    Returns:
        dict[Bit, str]:
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
    _, min_in_q_ai = _min_qarg(node, bits_abs_idx, n_controls)
    for q_ctrl in node.qargs[:n_controls]:
        tgt = min_in_q_ai - bits_abs_idx[q_ctrl]
        result[q_ctrl] = f"ctrl({tgt})"

    # Render controlled gate
    result.update(
        render_opnode(
            node=node,
            bits_abs_idx=bits_abs_idx,
            qargs_offset=n_controls,
            op_name=op_name,
        )
    )
    return result
