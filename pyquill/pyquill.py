"""Main module"""

# pylint: disable=protected-access

from collections import defaultdict

from qiskit.circuit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGCircuit, DAGOpNode

from . import renderers as rndr


def _clashes(node: DAGOpNode, layer: list[DAGOpNode]) -> bool:
    """
    Checks of `node` classes with any node in `layer`.

    Two opnodes are said to *clash* if their ranges overlap. In other words, if
    one opnodes first quibit index is between the other's first and last qubits
    indices. Visually, if one were to draw both gates on a quantum circuit
    diagram, they would overlap.
    """
    a1, a2 = _node_range(node)
    for n in layer:
        b1, b2 = _node_range(n)
        if a1 <= b1 <= a2 or b1 <= a1 <= b2:
            return True
    return False


def _node_range(node: DAGOpNode) -> tuple[int, int]:
    """
    A `DAGOpNode` range is a tuple containing the minimum and maximum
    indices of its input qubits. For example, if the node has input quibits 1,
    4, 5, then the range is (1, 5).
    """
    inputs = [i._index for i in node.qargs]
    return min(inputs), max(inputs)


def dag_layers(dag: DAGCircuit) -> dict[int, list[DAGOpNode]]:
    """
    Returns a dictionary of layers of opnodes. For example, the list at key `0`
    would be the set of all opnodes that can be ran in parallel at the begining
    of the circuit. Opnodes in each layer are guaranteed to not clash with
    other nodes in the same layer.
    """
    layers: dict[int, list[DAGOpNode]] = defaultdict(list)
    for node in dag.topological_op_nodes():
        clash_idx = -1  # Deepest layer to clash with node
        for j in sorted(layers.keys(), reverse=True):
            if _clashes(node, layers[j]):
                clash_idx = j
                break
        layers[clash_idx + 1].append(node)
    return layers


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
    dag = circuit_to_dag(qc)
    layers = dag_layers(dag)
    matrix = step2(dag, step1(layers))
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


def step1(
    layers: dict[int, list[DAGOpNode]]
) -> dict[int, dict[int, rndr.Renderer]]:
    """
    Takes a dictionary of layers of non-clashing opnodes (as produced by
    `dag_layers`) and returns a two level dictionnary of renderers. The the
    keys of the outer dictionary) are the qubit indices, and the inner
    dictionaries map a depth to gate renderer.

    In other words, if

        data = step1(layers)

    then `data[q][d]` is the renderer for the gate at depth `d` on qubit `q`,
    if such a gate exists.

    Args:
        layers (dict[int, list[DAGOpNode]]):

    Returns:
        dict[int, dict[int, rndr.Renderer]]:
    """
    result: dict[int, dict[int, rndr.Renderer]] = defaultdict(dict)
    for depth, layer in layers.items():
        for node in layer:
            # if node.name == "cx":
            if node.name == "cz":
                q_ctrl = int(node.qargs[0]._index)  # type: ignore
                q_tgt = int(node.qargs[1]._index)  # type: ignore
                result[q_ctrl][depth] = rndr.GateController(
                    target=q_tgt - q_ctrl
                )
                result[q_tgt][depth] = rndr.GateController(target=0)
            elif node.name == "cp":
                q_ctrl = int(node.qargs[0]._index)  # type: ignore
                q_tgt = int(node.qargs[1]._index)  # type: ignore
                theta = node.op.params[0]
                result[q_ctrl][depth] = rndr.ControlledPhaseGate(
                    target=q_tgt - q_ctrl, theta=theta
                )
                result[q_tgt][depth] = rndr.GateController(target=0)
            elif node.name.startswith("c"):  # controlled gate
                q_ctrl = int(node.qargs[0]._index)  # type: ignore
                q_tgt = int(node.qargs[1]._index)  # type: ignore
                result[q_ctrl][depth] = rndr.GateController(
                    target=q_tgt - q_ctrl
                )
                result[q_tgt][depth] = rndr.ControlledGate(
                    name=node.name[1:], width=1
                )
            else:
                a, b = _node_range(node)
                q = int(node.qargs[0]._index)  # type: ignore
                result[q][depth] = rndr.Gate(name=node.name, width=b - a + 1)
    return result


def step2(
    dag: DAGCircuit, renderers: dict[int, dict[int, rndr.Renderer]]
) -> list[list[str]]:
    """
    Takes the two-levels dictionary of renderers produced by `step1` and
    converts it into a matrix of instructions for the `quill` typst package.
    """
    depth = max(a for b in renderers.values() for a in b.keys()) + 1
    result: list[list[str]] = []
    for q_idx in range(dag.num_qubits()):
        u = renderers.get(q_idx, {})
        wire = [f"lstick($ket(psi_{q_idx})$)"]
        for d in range(depth):
            if g := u.get(d):
                wire.append(g.to_typst())
            else:
                wire.append("1")
        wire.append("1")
        if q_idx != dag.num_qubits() - 1:
            wire.append("[\\ ]")
        result.append(wire)
    return result
