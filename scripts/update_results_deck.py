"""Update the presented deck in place while preserving its visual template."""

from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt

DEFAULT_DECK = Path(
    "slides/Template-aulas-UNIFESSPA-FACSI-2026 (2) - trabalho-24-31 (1).pptx"
)
RESULTS = Path("data/securebert2_muse.json")
DIAGNOSTIC = Path("data/muse_validation_diagnostic.json")


def set_run_text(paragraph, text: str) -> None:
    if not paragraph.runs:
        paragraph.add_run().text = text
        return
    paragraph.runs[0].text = text
    for run in paragraph.runs[1:]:
        run.text = ""


def set_content(shape, paragraphs: list[str]) -> None:
    available = shape.text_frame.paragraphs
    slots = [0, 2, 4] if len(available) >= 5 else list(range(len(available)))
    for index, paragraph in enumerate(available):
        if index in slots:
            content_index = slots.index(index)
            set_run_text(
                paragraph,
                paragraphs[content_index] if content_index < len(paragraphs) else "",
            )
        else:
            set_run_text(paragraph, "")


def remove_old_diagram(slide) -> None:
    for shape in list(slide.shapes):
        if (
            shape.shape_type == 13
            and round(shape.width / 914400, 2) == 11.2
            and round(shape.height / 914400, 2) == 2.43
        ):
            shape._element.getparent().remove(shape._element)


def find_text_shape(slide, text: str | tuple[str, ...]):
    candidates = {text} if isinstance(text, str) else set(text)
    for shape in slide.shapes:
        if hasattr(shape, "text_frame") and shape.text.strip() in candidates:
            return shape
    raise ValueError(f"shape not found: {text}")


def find_shape_with_prefix(slide, prefix: str | tuple[str, ...]):
    candidates = (prefix,) if isinstance(prefix, str) else prefix
    for shape in slide.shapes:
        if hasattr(shape, "text_frame") and shape.text.startswith(candidates):
            return shape
    raise ValueError(f"shape prefix not found: {prefix}")


def update_deck(deck_path: Path, results_path: Path, diagnostic_path: Path) -> None:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    compatible = f"{results['compatible_exact']['f1']:.4f}".replace(".", ",")
    compatible_partial = f"{results['compatible_partial']['f1']:.4f}".replace(".", ",")
    typed_partial = {
        item["model"]: f"{item['partial_same_type']['f1']:.4f}".replace(".", ",")
        for item in diagnostic["models"]
    }
    presentation = Presentation(deck_path)

    slide5 = presentation.slides[4]
    set_run_text(
        find_text_shape(
            slide5, ("BASE | DADOS ENCONTRADOS", "DATASET UTILIZADO")
        ).text_frame.paragraphs[0],
        "DATASET UTILIZADO",
    )
    set_content(
        find_shape_with_prefix(slide5, ("1.066 registros", "1.627 documentos")),
        [
            (
                "1.627 documentos retidos: 1.621 do vinitvek/cybersecurityattacks "
                "e 6 do ScortonAI/Cyber-Security-Breaches."
            ),
            (
                "GVIC: 1.688 registros passaram pela triagem, mas nenhum foi retido "
                "como notícia de cibersegurança em saúde."
            ),
            (
                "Labels Muse: IDTY 1.640; ACT 1.423; LOC 117; VUL 51. "
                "Validação estrutural concluída; auditoria humana pendente."
            ),
        ],
    )

    slide6 = presentation.slides[5]
    set_run_text(
        find_text_shape(
            slide6, ("LIMITAÇÕES DA REPRODUÇÃO", "RESULTADOS PRELIMINARES")
        ).text_frame.paragraphs[0],
        "RESULTADOS PRELIMINARES",
    )
    content6 = find_shape_with_prefix(
        slide6, ("Corpus e anotações originais", "SecureBERT-NER:")
    )
    set_content(
        content6,
        [
            "SecureBERT-NER: Strict F1 = 0,1906 | Partial F1 = 0,4650.",
            "SecureBERT-APTNER: Strict F1 = 0,0597 | Partial F1 = 0,4840.",
            (
                f"SecureBERT 2.0: Strict F1 = {compatible} | "
                f"Partial F1 = {compatible_partial}*."
            ),
        ],
    )

    slide7 = presentation.slides[6]
    set_run_text(
        find_text_shape(
            slide7,
            (
                "PLANEJAMENTO DE REPRODUÇÃO",
                "LIMITAÇÕES E PRÓXIMOS PASSOS",
                "O QUE OS RESULTADOS INDICAM",
            ),
        ).text_frame.paragraphs[0],
        "O QUE OS RESULTADOS INDICAM",
    )
    content7 = find_shape_with_prefix(
        slide7,
        (
            "Separar notícias",
            "* SecureBERT 2.0",
            "Nota: SecureBERT 2.0",
            "O Partial com o mesmo tipo",
        ),
    )
    set_content(
        content7,
        [
            (
                "O Partial com o mesmo tipo permaneceu alto: "
                f"{typed_partial['SecureBERT-NER']} (NER) e "
                f"{typed_partial['SecureBERT-APTNER']} (APTNER)."
            ),
            (
                "A grande queda no Strict indica limites diferentes nos spans: "
                "o modelo encontra a região, mas não o início e o fim exatos."
            ),
            (
                "Próximo passo: auditar casos Partial que falharam no Strict e "
                "revisar os labels Muse antes da conclusão."
            ),
        ],
    )
    remove_old_diagram(slide7)

    references = find_shape_with_prefix(
        presentation.slides[7], "HUGGING FACE. CyberPeace-Institute/SecureBERT-NER."
    )
    reference_paragraphs = references.text_frame.paragraphs
    set_run_text(
        reference_paragraphs[3],
        "CISCO AI. SecureBERT2.0-NER. Hugging Face, 2025. Disponível em: "
        "https://huggingface.co/cisco-ai/SecureBERT2.0-NER. Acesso em: 14 set. 2026.",
    )
    for paragraph in reference_paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(13)

    presentation.save(deck_path)


def main() -> int:
    update_deck(DEFAULT_DECK, RESULTS, DIAGNOSTIC)
    print(f"Updated {DEFAULT_DECK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
