"""Generate a compact transparent diagram for insertion into a slide."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
from matplotlib.patches import Circle

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: I001


INK = "#172431"
ACCENT = "#176B78"
MUTED = "#536B78"
RULE = "#B9C8CF"


def add_phase(
    ax,
    x: float,
    number: str,
    title: str,
    primary: str,
    secondary: tuple[str, ...],
) -> None:
    """Draw one numbered phase and its labels on the reproduction diagram."""

    ax.add_patch(Circle((x, 1.75), 0.08, facecolor=ACCENT, edgecolor="none", zorder=3))
    ax.text(
        x,
        2.42,
        number,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color=ACCENT,
    )
    ax.text(
        x,
        2.16,
        title,
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color=INK,
    )
    ax.plot([x - 1.15, x + 1.15], [1.37, 1.37], color=RULE, linewidth=0.8, zorder=1)
    ax.text(
        x,
        1.04,
        primary,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=INK,
    )
    for index, text in enumerate(secondary):
        ax.text(
            x,
            0.70 - index * 0.26,
            text,
            ha="center",
            va="center",
            fontsize=10,
            color=MUTED,
        )


def build_diagram(output: Path) -> None:
    """Render the three-stage reproduction diagram to a transparent image."""

    fig, ax = plt.subplots(figsize=(15, 3.25), dpi=180)
    fig.patch.set_alpha(0)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 2.8)
    ax.axis("off")

    positions = (2.0, 7.5, 13.0)
    ax.plot(positions, [1.75] * 3, color=ACCENT, linewidth=1.15, zorder=1)
    add_phase(
        ax,
        positions[0],
        "01",
        "DADOS",
        "1.066 registros",
        ("limpeza · deduplicação", "60 notícias · 400 tokens"),
    )
    add_phase(
        ax,
        positions[1],
        "02",
        "INFERÊNCIA",
        "dois modelos",
        ("SecureBERT-NER", "SecureBERT-APTNER"),
    )
    add_phase(
        ax,
        positions[2],
        "03",
        "AVALIAÇÃO",
        "Strict · Partial",
        ("IDTY · ACT · VUL · LOC", "P · R · F1 · baseline manual"),
    )

    ax.text(
        7.5,
        0.20,
        "reprodução aproximada  ·  desvios registrados",
        ha="center",
        va="bottom",
        fontsize=8.8,
        color=MUTED,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(output, dpi=180, transparent=True, pad_inches=0)
    plt.close(fig)


def main() -> int:
    """Parse the output path, generate the diagram, and return a CLI status."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("slides/reproduction_plan_diagram.png"))
    args = parser.parse_args()
    build_diagram(args.output)
    print(f"Generated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
