"""Main module"""

# pylint: disable=protected-access

from collections import defaultdict

from qiskit.circuit import QuantumCircuit, Qubit
from qiskit.visualization.circuit._utils import (
    _get_layered_instructions as get_layered_instructions,
)

from .render import render_opnode


def draw(
    qc: QuantumCircuit, leading_hash: bool = True, imports: bool = False
) -> str:
    """
    Renders a quantum circuit in typst using the `quantum-circuit` environment
    of the [`quill` package](https://typst.app/universe/package/quill).

    Args:
        qc (QuantumCircuit):
        leading_hash (bool, optional):
        imports (bool, optional): Does not override `leading_hash`, i.e. it is
            possible (but not desirable) to have `leading_hash=False` but
            `imports=True`.
    """
    matrix = step2(qc, step1(qc))
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


# TODO: Find a better name
def step1(qc: QuantumCircuit) -> dict[Qubit, dict[int, str]]:
    """
    Generates a two-levels dictionary of typst instruction for each qubit in
    the input quantum circuit.

    If `qc` is a quantum circuit, then `step1(qc)[q][d]` is a typst instruction
    for a gate for qubit `q` at depth `d`.

    Args:
        qc (QuantumCircuit):

    Returns:
        dict[Qubit, dict[int, str]]:
    """
    _, _, layers = get_layered_instructions(qc)
    indices: dict[Qubit, int] = {q: i for i, q in enumerate(qc.qubits)}
    result: dict[Qubit, dict[int, str]] = defaultdict(dict)
    for depth, layer in enumerate(layers):
        for node in layer:
            for q, r in render_opnode(node, indices).items():
                result[q][depth] = r
    return result


# TODO: Find a better name
def step2(
    qc: QuantumCircuit, renderers: dict[Qubit, dict[int, str]]
) -> list[list[str]]:
    """
    Takes the two-levels dictionary of renderers produced by `step1` and
    converts it into a matrix of instructions for the `quill` typst package.
    """
    depth = max(a for b in renderers.values() for a in b.keys()) + 1
    result: list[list[str]] = []
    for i, q in enumerate(qc.qubits):
        u = renderers.get(q, {})
        wire = [f"lstick($ket({q._register.name}_{q._index})$)"]
        for d in range(depth):
            wire.append(u.get(d, "1"))
        wire.append("1")
        if i != qc.num_qubits - 1:
            wire.append("[\\ ]")
        result.append(wire)
    return result
