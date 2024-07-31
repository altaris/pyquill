"""
Dataclasses to encapsulate rendering information for gates etc.
"""

# pylint: disable=protected-access

import re
from typing import TypeAlias

from qiskit.circuit import ClassicalRegister, Qubit
from qiskit.dagcircuit import DAGOpNode

from .typst import as_fraction_of_pi

Wire: TypeAlias = Qubit | ClassicalRegister


def _min_max_qarg(
    node: DAGOpNode, wires_abs_idx: dict[Wire, int], qargs_offset: int = 0
) -> tuple[Qubit, int, Qubit, int]:
    """
    Return the input qubit with the minimum wire index, said index, the input
    qubit with the maximum wire index, and said index. If `qargs_offset` is
    specified, only consider qargs starting from that index.
    """
    min_q = max_q = node.qargs[qargs_offset]
    min_ai = max_ai = wires_abs_idx[node.qargs[qargs_offset]]
    for q in node.qargs[qargs_offset:]:
        ai = wires_abs_idx[q]
        if ai < min_ai:
            min_q, min_ai = q, ai
        if ai > max_ai:
            max_q, max_ai = q, ai
    return min_q, min_ai, max_q, max_ai


def _n_wires(
    node: DAGOpNode, wires_abs_idx: dict[Wire, int], qargs_offset: int = 0
) -> int:
    """
    Return the width of the gate, i.e. the number of wires it spans over. If
    `qargs_offset` is specified, only consider qargs starting from that index.
    """
    iai = [wires_abs_idx[q] for q in node.qargs[qargs_offset:]]
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
        "inner_product": '"InnerProd."',
        "xx_minus_yy": "$(X X - Y Y) ({0}, {1})$",
        "xx_plus_yy": "$(X X + Y Y) ({0}, {1})$",
        # "ms": '"GMS"',  # TODO:
        # "pauli": "$$", # TODO: maybe?
        # "prepare_state": "State Preparation",  # TODO:
    }
    if typst := easy_gates.get(op_name):
        if op_name == "rv":
            # Exception: RV gate params are not expected to be fractions of pi
            return typst.format(*parameters)
        return typst.format(*map(as_fraction_of_pi, parameters))
    if re.match(r"^\w+$", op_name):
        return f'"{op_name.upper()}"'
    return op_name


def render_gate_box(
    node: DAGOpNode,
    wires_abs_idx: dict[Wire, int],
    n_controls: int = 0,
    op_name: str | None = None,
) -> str:
    """
    Renders a gate which can be represented as a box, e.g. `H` or `RXX`, but not
    `X`, `RZZ` or a phase gate.

    Args:
        node (DAGOpNode):
        wires_abs_idx (dict[Wire, int]):
        n_controls (int, optional):
        op_name (str | None, optional): To override the node's name.

    Returns:
        str:
    """
    tpst = easy_op_to_typst(op_name or node.name[n_controls:], node.op.params)
    _, min_qarg_wi, _, max_qarg_wi = _min_max_qarg(
        node, wires_abs_idx, n_controls
    )
    n_wires = max_qarg_wi - min_qarg_wi + 1
    if n_wires == 1:
        return tpst
    inputs = []
    relative_wi = {q: wires_abs_idx[q] - min_qarg_wi for q in node.qargs}
    for i, q in enumerate(node.qargs[n_controls:]):
        inputs.append(f'(qubit: {relative_wi[q]}, label: "{i}")')
    for q in node.qargs[:n_controls]:  # Controls overlapped by the gate
        if not min_qarg_wi < wires_abs_idx[q] < max_qarg_wi:
            continue
        inputs.append(f"(qubit: {relative_wi[q]}, label: $bullet$)")
    inputs_arr_str = ", ".join(inputs)
    width = 5.0
    if n_wires % 2 == 1 and n_wires // 2 in list(relative_wi.values()):
        # There's an input or control in the middle of the gate. Increase width
        # to (hopefully) not overlap with gate label.
        width += 1.5
    return f"mqgate({tpst}, n: {n_wires}, inputs: ({inputs_arr_str}), width: {width}em)"


# pylint: disable=too-many-branches
def render_opnode(
    node: DAGOpNode,
    wires_abs_idx: dict[Wire, int],
    qargs_offset: int = 0,
    op_name: str | None = None,
    ignore_conditions: bool = False,
) -> dict[Wire, str]:
    """
    Given an opnode and a mapping of qubits to their absolute indices, returns
    a dict that maps the input qubits of that node to a typst instruction that
    should be put to that qubit's wire.

    Args:
        node (DAGOpNode):
        wires_abs_idx (dict[Qubit, int]): Mapping of bits (quantum and classical)
            to their absolute wire indices.
        qargs_offset (int, optional): If set, the first `qargs_offset` qargs
            are ignored.
        op_name (str | None, optional): To override the node's name.

    Returns:
        dict[Wire, str]:
    """
    op_name, qargs = op_name or node.name, node.qargs[qargs_offset:]
    result: dict[Wire, str] = {}

    # Gate with a classical condition
    if node.op.condition and not ignore_conditions:
        return render_opnode_cond(
            node, wires_abs_idx, qargs_offset=qargs_offset, op_name=op_name
        )

    # Special cases
    if op_name == "barrier":
        result[qargs[0]] = (
            f'slice(n: {len(qargs)}, stroke: (paint: black, dash: "dashed"))'
        )
        for q in wires_abs_idx:
            if q != qargs[0]:
                result[q] = "0"
    elif op_name == "cp":
        q0, q1 = qargs[:2]
        ri = wires_abs_idx[q1] - wires_abs_idx[q0]
        if ri < 0:
            ri, q0, q1 = -ri, q1, q0
        theta = as_fraction_of_pi(node.op.params[0])
        result[q0] = (
            f"ctrl({ri}, wire-label: (content: ${theta}$, pos: top, dy: -0.75em))"
        )
        result[q1] = "ctrl(0)"
    elif op_name == "cz":
        q0, q1 = qargs[:2]
        ri = wires_abs_idx[q1] - wires_abs_idx[q0]
        result[q0], result[q1] = f"ctrl({ri})", "ctrl(0)"
    elif op_name.startswith("GR("):
        new_op_name = "gr"
        if op_name.endswith("0.00)"):
            new_op_name += "x"
        elif op_name.endswith("1.57)"):
            new_op_name += "y"
        return render_opnode(
            node=node,
            wires_abs_idx=wires_abs_idx,
            qargs_offset=qargs_offset,
            op_name=new_op_name,
            ignore_conditions=ignore_conditions,
        )
    elif op_name == "measure":
        q0, c0 = qargs[0], node.cargs[0]
        r0: ClassicalRegister = c0._register
        ri = wires_abs_idx[r0] - wires_abs_idx[q0]
        result[q0] = f"meter(target: {ri})"
        result[r0] = f"ctrl(0, label: ((content: ${c0._index}$, pos: bottom)))"
    elif op_name == "p":
        theta = as_fraction_of_pi(node.op.params[0])
        result[qargs[0]] = (
            f"phase((content: ${theta}$, pos: top, dy: -0.75em))"
        )
    elif op_name == "PauliEvolution":
        a, b = node.op.label, node.op.params[0]
        return render_opnode(
            node=node,
            wires_abs_idx=wires_abs_idx,
            qargs_offset=qargs_offset,
            op_name=f'"{a} ({b})"',
            ignore_conditions=ignore_conditions,
        )
    elif op_name == "rzz":
        q0, q1 = qargs[:2]
        ri = wires_abs_idx[q1] - wires_abs_idx[q0]
        theta = as_fraction_of_pi(node.op.params[0])
        result[q0] = f"ctrl({ri}, wire-label: $Z Z ({theta})$)"
        result[q1] = "ctrl(0)"
    elif op_name == "swap":
        q0, q1 = qargs[:2]
        ri = wires_abs_idx[q1] - wires_abs_idx[q0]
        result[q0], result[q1] = f"swap({ri})", "targX()"
    elif op_name == "x" and node.op.name.endswith("cx"):
        result[qargs[0]] = "targ()"

    # Controlled gate
    elif op_name.startswith("c") and len(qargs) >= 2:
        # TODO: make a recursive call to render_opnode instead?
        return render_opnode_crtl(
            node=node,
            wires_abs_idx=wires_abs_idx,
            ignore_conditions=ignore_conditions,
        )

    # Generic (boxed) gate
    else:
        min_qarg, _, _, _ = _min_max_qarg(node, wires_abs_idx, qargs_offset)
        result[min_qarg] = render_gate_box(
            node=node,
            wires_abs_idx=wires_abs_idx,
            n_controls=qargs_offset,
            op_name=op_name,
        )

    return result


def render_opnode_cond(
    node: DAGOpNode, wires_abs_idx: dict[Wire, int], **kwargs
) -> dict[Wire, str]:
    """
    Like `render_opnode`, but for a gates with a condition on a classical
    register. `node.op.condition` cannot be `None`.


    Args:
        node (DAGOpNode):
        wires_abs_idx (dict[Wire, int]):

    Returns:
        dict[Wire, str]:
    """
    if not node.op.condition:
        raise ValueError("This function is only accepts conditioned gates.")
    result = {}
    _, _, _, qi = _min_max_qarg(node, wires_abs_idx)
    c, val = node.op.condition
    tgt = qi - wires_abs_idx[c]
    result[c] = (
        f"ctrl({tgt}, label: ((content: ${val}$, pos: bottom)), wire-count: 2)"
    )
    # Render conditioned gate
    result.update(
        render_opnode(
            node=node,
            wires_abs_idx=wires_abs_idx,
            ignore_conditions=True,
            **kwargs,
        )
    )
    return result


def render_opnode_crtl(
    node: DAGOpNode, wires_abs_idx: dict[Wire, int], **kwargs
) -> dict[Wire, str]:
    """
    Like `render_opnode`, but for controlled gates. The node's opname must start
    with a 'c'.

    Args:
        node (DAGOpNode):
        wires_abs_idx (dict[Wire, int]):

    Returns:
        dict[Wire, str]:
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
    _, min_qarg_wi, _, max_qarg_wi = _min_max_qarg(
        node, wires_abs_idx, n_controls
    )
    for q_ctrl in node.qargs[:n_controls]:
        if min_qarg_wi < wires_abs_idx[q_ctrl] < max_qarg_wi:
            # Gate overlaps with control. This case is handled by
            # render_gate_box
            continue
        tgt = min_qarg_wi - wires_abs_idx[q_ctrl]
        result[q_ctrl] = f"ctrl({tgt})"

    # Render controlled gate
    result.update(
        render_opnode(
            node=node,
            wires_abs_idx=wires_abs_idx,
            qargs_offset=n_controls,
            op_name=op_name,
            **kwargs,
        )
    )
    return result
