# pylint: disable=invalid-name
# pylint: disable=missing-function-docstring

from pathlib import Path

import numpy as np
import typst
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import *

from pyquill import draw

OUTPUT_DIR = Path("tests")


def test_simple() -> QuantumCircuit:
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.p(np.pi / 2, 0)
    qc.barrier()
    qc.sx(1)
    qc.cx(1, 0)
    qc.sxdg(1)
    qc.z(2)
    qc.swap(1, 2)
    qc.barrier()
    return qc


def test_1_qubit_gates() -> QuantumCircuit:
    gates = [
        [  # Noneparametric
            XGate(),
            YGate(),
            ZGate(),
            HGate(),
            SGate(),
            SdgGate(),
            SXGate(),
            SXdgGate(),
            TGate(),
            TdgGate(),
            IGate(),
        ],
        [  # 1 parameter
            PhaseGate(np.pi),
            RGate(np.pi, np.pi / 4),
            RXGate(np.pi),
            RYGate(np.pi),
            RZGate(np.pi),
        ],
        [  # 2 parameters
            U2Gate(np.pi / 4, np.pi / 8),
        ],
        [  # 3 parameter
            UGate(np.pi / 2, np.pi / 4, np.pi / 8),
            RVGate(0.1, 0.2, 0.3),
        ],
    ]
    qc = QuantumCircuit(len(gates))
    for i, g in enumerate(gates):
        for u in g:
            qc.append(u, [i])
    return qc


def test_2_qubit_gates() -> QuantumCircuit:
    gates = [
        [  # Noneparametric
            DCXGate(),
            ECRGate(),
            iSwapGate(),
        ],
        [  # 1 parameter
            RXXGate(np.pi),
            RYYGate(np.pi),
            RZZGate(np.pi),
            RZXGate(np.pi),
        ],
        [],  # 2 parameters
        [],  # 3 parameter
    ]
    qc = QuantumCircuit(2 * len(gates))
    for i, g in enumerate(gates):
        for u in g:
            qc.append(u, [2 * i, 2 * i + 1])
    return qc


def test_input_indices() -> QuantumCircuit:
    qc = QuantumCircuit(3)
    qc.rxx(np.pi, 0, 1)
    qc.rxx(np.pi, 1, 0)
    qc.barrier()
    qc.rxx(np.pi, 1, 2)
    qc.rxx(np.pi, 2, 1)
    qc.barrier()
    qc.rxx(np.pi, 0, 2)
    qc.rxx(np.pi, 2, 0)
    return qc


def test_parallel_cx() -> QuantumCircuit:
    qc = QuantumCircuit(4)
    qc.cx(0, 1)
    qc.cx(3, 2)
    qc.cy(0, 2)
    qc.cy(3, 1)
    qc.cy(0, 2)
    return qc


def test_cphase() -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.cz(0, 1)
    qc.h(0)
    qc.cp(np.pi, 0, 1)
    qc.h(0)
    qc.cp(np.pi / 2, 0, 1)
    qc.h(0)
    qc.cp(3 * np.pi / 4, 0, 1)
    qc.h(0)
    qc.cp(-np.pi / 4, 0, 1)
    qc.h(0)
    qc.cp(-3 * np.pi, 0, 1)
    qc.h(0)
    qc.cp(0.1, 0, 1)
    return qc


def test_register() -> QuantumCircuit:
    a = QuantumRegister(2, "psi")
    b = QuantumRegister(3, "phi")
    qc = QuantumCircuit(a, b)
    qc.h(a[0])
    qc.cx(a[0], b[2])
    return qc


def test_controls() -> QuantumCircuit:
    qc = QuantumCircuit(5)
    qc.cswap(2, 0, 1)
    qc.cswap(1, 0, 2)
    qc.cswap(0, 1, 2)
    qc.barrier()
    qc.ccx(0, 1, 2)
    qc.ccx(2, 0, 1)
    qc.ccx(2, 1, 0)
    qc.barrier()
    qc.append(HGate().control(3), [0, 1, 2, 3])
    qc.append(HGate().control(3), [3, 0, 1, 2])
    qc.append(HGate().control(3), [2, 3, 0, 1])
    qc.append(HGate().control(3), [1, 2, 3, 0])
    qc.barrier()
    qc.append(RXXGate(3 * np.pi / 2).control(3), [0, 1, 2, 3, 4])
    qc.append(RXXGate(3 * np.pi / 2).control(3), [4, 0, 1, 2, 3])
    qc.append(RXXGate(3 * np.pi / 2).control(3), [3, 4, 0, 1, 2])
    qc.append(RXXGate(3 * np.pi / 2).control(3), [2, 3, 4, 0, 1])
    return qc


def test_controls_overlap() -> QuantumCircuit:
    qc = QuantumCircuit(5)
    qc.append(RXXGate(np.pi).control(1), [1, 0, 4])
    qc.append(RXXGate(np.pi).control(1), [2, 0, 4])
    qc.append(RXXGate(np.pi).control(1), [3, 0, 4])
    qc.barrier()
    qc.append(RXXGate(np.pi).control(2), [1, 2, 0, 4])
    qc.append(RXXGate(np.pi).control(2), [1, 3, 0, 4])
    qc.append(RXXGate(np.pi).control(2), [2, 4, 0, 3])
    qc.barrier()
    qc.append(RXXGate(np.pi).control(3), [1, 2, 3, 0, 4])
    qc.append(RXXGate(np.pi).control(3), [0, 2, 4, 1, 3])
    return qc


def test_conditions() -> QuantumCircuit:
    q, c = QuantumRegister(4, "psi"), ClassicalRegister(2, "c")
    qc = QuantumCircuit(q, c)
    qc.h(q[0]).c_if(c, 0)
    # qc.h(q[1]).c_if(c, 1)
    qc.h(q[2]).c_if(c, 2)
    qc.barrier()
    qc.append(TdgGate().control(3), [q[1], q[2], q[3], q[0]]).c_if(c, 0)
    # qc.append(TdgGate().control(3), [q[2], q[3], q[0], q[1]]).c_if(c, 1)
    qc.append(TdgGate().control(3), [q[3], q[0], q[1], q[2]]).c_if(c, 2)
    qc.barrier()
    qc.swap(q[0], q[1]).c_if(c, 0)
    qc.swap(q[1], q[2]).c_if(c, 1)
    qc.swap(q[2], q[0]).c_if(c, 2)
    qc.barrier()
    qc.cx(q[0], q[1]).c_if(c, 0)
    qc.cx(q[1], q[2]).c_if(c, 1)
    qc.cx(q[2], q[0]).c_if(c, 2)
    qc.barrier()
    qc.append(RZXGate(np.pi).control(2), [q[2], q[3], q[0], q[1]]).c_if(c, 0)
    qc.append(RZXGate(np.pi).control(2), [q[0], q[1], q[2], q[3]]).c_if(c, 2)
    qc.append(RZXGate(np.pi).control(2), [q[3], q[0], q[1], q[2]]).c_if(c, 3)
    return qc


def test_measure() -> QuantumCircuit:
    qc = QuantumCircuit(2, 4)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    qc.barrier()
    qc.measure(0, 3)
    qc.measure(1, 2)
    qc.measure_all()
    qc.measure_all()
    return qc


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    preamble = (
        '#import "@preview/physica:0.9.3": *\n'
        '#import "@preview/quill:0.3.0": *\n'
        '#set page("a4", flipped: true, numbering: "1 / 1")\n'
        '#set heading(numbering: "1.")\n'
    )
    test_functions = {
        k: v
        for k, v in globals().items()
        if k.startswith("test_") and callable(v)
    }
    renderings: dict[str, tuple[str, str]] = {}
    for name, test in test_functions.items():
        print(name)
        qc = test()
        a, b = qc.draw(fold=-1), draw(qc)
        renderings[name] = a, b
        file_path = OUTPUT_DIR / f"{name}.typ"
        with file_path.open("w", encoding="utf-8") as fp:
            fp.write(preamble)
            fp.write(f"= `{name}`\n```\n{a}\n```\n{b}")
        typst.compile(file_path, file_path.with_suffix(".pdf"))
    file_path = OUTPUT_DIR / "all.typ"
    with file_path.open("w", encoding="utf-8") as fp:
        fp.write(preamble)
        for name, (a, b) in renderings.items():
            fp.write(f"= `{name}`\n```\n{a}\n```\n{b}\n#pagebreak()\n")
    typst.compile(file_path, file_path.with_suffix(".pdf"))
