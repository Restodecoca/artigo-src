"""Insert the standalone reproduction diagram into one slide."""

from __future__ import annotations

import argparse
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches


def insert_diagram(
    input_path: Path,
    output_path: Path,
    image_path: Path,
    slide_number: int,
    x: float,
    y: float,
    width: float,
) -> None:
    presentation = Presentation(input_path)
    if not 1 <= slide_number <= len(presentation.slides):
        raise ValueError(f"Slide {slide_number} is outside the presentation")
    slide = presentation.slides[slide_number - 1]
    slide.shapes.add_picture(str(image_path), Inches(x), Inches(y), width=Inches(width))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--slide", type=int, default=10)
    parser.add_argument("--x", type=float, default=1.05)
    parser.add_argument("--y", type=float, default=4.35)
    parser.add_argument("--width", type=float, default=11.2)
    args = parser.parse_args()
    insert_diagram(args.input, args.output, args.image, args.slide, args.x, args.y, args.width)
    print(f"Inserted {args.image} into slide {args.slide}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
