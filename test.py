# pylint: disable=invalid-name
# pylint: disable=missing-function-docstring

from pathlib import Path

import typst
from qiskit import QuantumCircuit

from pyquill import draw

OUTPUT_FILE = Path("test/test.typ")


def test_simple() -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.h(1)
    return qc


def test_parallel_cx() -> QuantumCircuit:
    qc = QuantumCircuit(4)
    qc.cx(0, 1)
    qc.cx(2, 3)
    qc.cy(0, 2)
    qc.cy(1, 3)
    qc.cy(0, 2)
    return qc


if __name__ == "__main__":
    content = (
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
    for name, test in test_functions.items():
        print(name)
        qc = test()
        a, b = qc.draw(fold=-1), draw(qc)
        content += f"= `{name}`\n```\n{a}\n```\n{b}\n#pagebreak()\n"
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open(mode="w", encoding="utf-8") as fp:
        fp.write(content)
    typst.compile(OUTPUT_FILE, OUTPUT_FILE.with_suffix(".pdf"))
