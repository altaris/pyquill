"""Main module"""

# pylint: disable=protected-access

from collections import defaultdict

from qiskit.circuit import QuantumCircuit
from qiskit.visualization.circuit._utils import (
    _get_layered_instructions as get_layered_instructions,
)

from .render import Wire, render_opnode
from .typst import wire_name


# TODO: Find a better name
def _step1(qc: QuantumCircuit) -> dict[Wire, dict[int, str]]:
    """
    Generates a two-levels dictionary of typst instruction for each bit (quantum
    and classical) in the input quantum circuit.

    If `qc` is a quantum circuit, then `step1(qc)[q][d]` is a typst instruction
    for a gate for qubit `q` at depth `d`.

    Args:
        qc (QuantumCircuit):

    Returns:
        dict[Bit, dict[int, str]]:
    """
    _, _, layers = get_layered_instructions(qc)
    indices: dict[Wire, int] = {
        q: i for i, q in enumerate(qc.qubits + qc.cregs)
    }
    result: dict[Wire, dict[int, str]] = defaultdict(dict)
    for depth, layer in enumerate(layers):
        for node in layer:
            for q, r in render_opnode(node, indices).items():
                result[q][depth] = r
    return result


# TODO: Find a better name
def _step2(
    qc: QuantumCircuit, renderers: dict[Wire, dict[int, str]]
) -> list[list[str]]:
    """
    Takes the two-levels dictionary of typst instruction strings produced by
    `_step1` and converts it into a matrix of instructions for the `quill` typst
    package.
    """
    depth = max(a for b in renderers.values() for a in b.keys()) + 1
    result: list[list[str]] = []
    for i, q in enumerate(qc.qubits):
        u, wn = renderers.get(q, {}), wire_name(q._register, q._index)
        wire = [f"lstick({wn})"]
        if any(r.size > 1 for r in qc.cregs):
            # Some classical wires will have the nwire(...) instruction
            wire.append("1")
        for d in range(depth):
            wire.append(u.get(d, "1"))
        wire.append("1")
        if qc.cregs or i < qc.num_qubits - 1:
            wire.append("[\\ ]")
        result.append(wire)
    for i, r in enumerate(qc.cregs):
        u, wn = renderers.get(r, {}), wire_name(r)
        wire = [f"lstick({wn})", "setwire(2)"]
        if r.size > 1:
            wire.append(f"nwire({r.size})")
        for d in range(depth):
            wire.append(u.get(d, "1"))
        if i < len(qc.cregs) - 1:
            wire.append("[\\ ]")
        result.append(wire)
    return result


def draw(
    qc: QuantumCircuit, leading_hash: bool = True, imports: bool = False
) -> str:
    """
    Draws a quantum circuit in typst using the `quantum-circuit` environment
    of the [`quill` package](https://typst.app/universe/package/quill).

    Args:
        qc (QuantumCircuit):
        leading_hash (bool, optional): Wether the typst code should look like
            `#quantum-circuit(...)` or `quantum-circuit(...)`.
        imports (bool, optional): If set to `True`, packages
            `@preview/physica:0.9.3` and `@preview/quill:0.3.0` are fully imported.
            Otherwise, no import directive are prepended to the output. This
            option does not override `leading_hash`, i.e. it is possible (but
            not desirable) to have `leading_hash=False` but `imports=True`.
    """
    matrix = _step2(qc, _step1(qc))
    result = ",".join(",".join(row) for row in matrix)
    result = "quantum-circuit(" + result + ")"
    if leading_hash:
        result = "#" + result
    if imports:
        result = (
            "\n".join(
                [
                    '#import "@preview/physica:0.9.3": *',
                    '#import "@preview/quill:0.3.0": *',
                ]
            )
            + "\n"
            + result
        )
    return result
