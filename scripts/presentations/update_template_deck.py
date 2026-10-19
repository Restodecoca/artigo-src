"""Populate the course template with the two missed/presented milestones."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast
from xml.dom import minidom

PRESENTATION_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
RELATIONSHIP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def text_nodes(document: minidom.Document):
    """Return all DrawingML text nodes from a presentation XML document."""

    return document.getElementsByTagName("a:t")


def node_text(node) -> str:
    """Read the text value from a populated XML text node."""

    return cast(minidom.Text, node.firstChild).data


def set_node_text(node, value: str) -> None:
    """Replace the text value of an existing XML text node."""

    cast(minidom.Text, node.firstChild).data = value


def replace_text(document: minidom.Document, old: str, new: str) -> None:
    """Replace exact matching text-node values throughout a slide document."""

    for node in text_nodes(document):
        if node.firstChild is not None and node_text(node) == old:
            set_node_text(node, new)


def replace_texts(document: minidom.Document, replacements: dict[str, str]) -> None:
    """Apply a mapping of exact text substitutions to populated XML nodes."""

    for node in text_nodes(document):
        if node.firstChild is not None:
            replacement = replacements.get(node_text(node))
            if replacement is not None:
                set_node_text(node, replacement)


def set_footer_page(document: minidom.Document, page: str) -> None:
    """Set the page number in the template's known footer shape."""

    for shape in document.getElementsByTagName("p:sp"):
        offsets = shape.getElementsByTagName("a:off")
        if not offsets or offsets[0].getAttribute("x") != "11292840":
            continue
        numbers = [node for node in shape.getElementsByTagName("a:t") if node.firstChild]
        if numbers:
            set_node_text(numbers[0], page)
        return


def fit_cover_authors(document: minidom.Document) -> None:
    """Widen the cover author shape when it contains the expected author line."""

    target = "Gabriel Rodrigues | Gabriel Machado | Angelo Resplandes"
    for shape in document.getElementsByTagName("p:sp"):
        content = "".join(
            node_text(node) for node in shape.getElementsByTagName("a:t") if node.firstChild
        )
        if content != target:
            continue
        extents = shape.getElementsByTagName("a:ext")
        if extents:
            extents[0].setAttribute("cx", "5200000")
        return


def write_document(path: Path, document: minidom.Document) -> None:
    """Serialize a presentation XML document to UTF-8 at the given path."""

    path.write_text(document.toxml(encoding="utf-8").decode("utf-8"), encoding="utf-8")


def load_document(path: Path) -> minidom.Document:
    """Parse an XML presentation part from disk."""

    return minidom.parse(str(path))


def apply_common_footer(document: minidom.Document) -> None:
    """Replace known template footer variants with the course footer."""

    for old in (
        "TEMPLATE | MODELO EDITÁVEL",
        "TEMPLATE | MDELO EDITÁVEL",
        "TEMPLATE | CONTEÚDO",
        "SEGURANÇA EM REDES | PROF. HUGO KURIBAYASHI",
    ):
        replace_text(document, old, "SEGURANÇA EM REDES | SI 2024")


def set_bullet_sequence(document: minidom.Document) -> None:
    """Renumber populated automatic bullets and remove bullets from empty rows."""

    number = 1
    for paragraph in document.getElementsByTagName("a:p"):
        auto_numbers = paragraph.getElementsByTagName("a:buAutoNum")
        if not auto_numbers:
            continue
        content = "".join(
            node_text(node) for node in paragraph.getElementsByTagName("a:t") if node.firstChild
        ).strip()
        if not content:
            bu_none = document.createElementNS(DRAWING_NS, "a:buNone")
            parent = auto_numbers[0].parentNode
            if parent is not None:
                parent.replaceChild(bu_none, auto_numbers[0])
            continue
        auto_numbers[0].setAttribute("startAt", str(number))
        number += 1


def format_reference_list(document: minidom.Document) -> None:
    """Normalize alignment, spacing, and font size in the reference list."""

    for paragraph in document.getElementsByTagName("a:p"):
        auto_numbers = paragraph.getElementsByTagName("a:buAutoNum")
        if not auto_numbers:
            continue
        paragraph_properties = paragraph.getElementsByTagName("a:pPr")
        if not paragraph_properties:
            continue
        paragraph_properties[0].setAttribute("algn", "l")
        paragraph_properties[0].setAttribute("marL", "0")
        paragraph_properties[0].setAttribute("indent", "0")
        parent = auto_numbers[0].parentNode
        if parent is not None:
            bullet_none = document.createElementNS(DRAWING_NS, "a:buNone")
            parent.replaceChild(bullet_none, auto_numbers[0])
        for spacing in paragraph.getElementsByTagName("a:lnSpc"):
            percentages = spacing.getElementsByTagName("a:spcPct")
            if percentages:
                percentages[0].setAttribute("val", "100000")
        for spacing in paragraph.getElementsByTagName("a:spcAft"):
            points = spacing.getElementsByTagName("a:spcPts")
            if points:
                points[0].setAttribute("val", "6000")
        for run_properties in paragraph.getElementsByTagName("a:rPr"):
            run_properties.setAttribute("sz", "1600")
        for end_properties in paragraph.getElementsByTagName("a:endParaRPr"):
            end_properties.setAttribute("sz", "1600")
    set_font_size(document, "1300", "1600")


def format_methodology_list(document: minidom.Document) -> None:
    """Increase the methodology slide's designated text size."""

    set_font_size(document, "1300", "1900")


def set_font_size(document: minidom.Document, old: str, new: str) -> None:
    """Replace matching DrawingML run and paragraph font-size values."""

    for tag in ("a:rPr", "a:endParaRPr"):
        for properties in document.getElementsByTagName(tag):
            if properties.getAttribute("sz") == old:
                properties.setAttribute("sz", new)


def remove_edit_markers(document: minidom.Document) -> None:
    """Remove residual ``[EDITAR]`` placeholders from presentation text."""

    for node in text_nodes(document):
        if node.firstChild is not None and "[EDITAR]" in node_text(node):
            set_node_text(node, node_text(node).replace("[EDITAR]", "").strip())


def edit_slides(slides_dir: Path) -> None:
    """Apply slide-specific text replacements and template formatting updates."""

    replacements: dict[str, dict[str, str]] = {
        "slide1.xml": {
            "[EDITAR] TÍTULO": "TRABALHO DE GRUPO",
            "DA AULA": "FINAL",
            "[EDITAR] subtítulo ou unidade temática": "1º e 2º marcos | Reprodução de artigo científico",
            "[EDITAR] docente | disciplina | 2026": "Gabriel Rodrigues | Gabriel Machado | Angelo Resplandes",
            "Segurança em Redes de Computadores | SI 2024 | 31/08": "Gabriel Rodrigues | Gabriel Machado | Angelo Resplandes",
            "SI 2024 | Segurança em Redes | 31/08": "Gabriel Rodrigues | Gabriel Machado | Angelo Resplandes",
            "Gabriel Rodrigues | Gabriel Machado": "Gabriel Rodrigues | Gabriel Machado | Angelo Resplandes",
        },
        "slide2.xml": {
            "COMO EDITAR": "ENTREGA DOS MARCOS",
            "ENTREGA DOS MARCOS": "OBJETIVO DA APRESENTAÇÃO",
            "Substitua os textos entre colchetes.": "Apresentar o artigo selecionado e seu contexto.",
            "1º marco: equipe e artigo escolhido.": "Apresentar o artigo selecionado e seu contexto.",
            "Mantenha a logo, as margens e a hierarquia tipográfica.": "Discutir a problemática, os objetivos e a metodologia reportada.",
            "2º marco (31/08): contexto, objetivos e metodologia.": "Discutir a problemática, os objetivos e a metodologia reportada.",
            "2º marco (31/08): contexto, problemática, objetivos, metodologia e planejamento.": "Discutir a problemática, os objetivos e a metodologia reportada.",
            "Remova esta lâmina antes de apresentar": "Definir o planejamento da reprodução aproximada.",
            "Os dois marcos serão apresentados nesta entrega.": "Definir o planejamento da reprodução aproximada.",
        },
        "slide3.xml": {
            "SUMÁRIO": "ROTEIRO",
            "[EDITAR] abertura / contexto": "Artigo selecionado",
            "Apresentação conjunta dos dois marcos": "Artigo selecionado",
            "[EDITAR] conceito principal": "Contexto e problemática",
            "Escolha e contexto do artigo": "Contexto e problemática",
            "[EDITAR] exemplo ou aplicação": "Objetivos e metodologia",
            "Metodologia e dados encontrados": "Objetivos e metodologia",
            "[EDITAR] síntese / discussão": "Limitações e planejamento",
        },
        "slide4.xml": {
            "[EDITAR] TÍTULO DO TÓPICO": "CONTEXTO DO ARTIGO",
            "POR QUE ESTE ARTIGO?": "CONTEXTO DO ARTIGO",
            "[EDITAR] ideia principal": "Artigo escolhido: An Analysis of Pre-trained Models to Identify Cybersecurity Incidents Entities in the Healthcare Industry.",
            "Tema ligado à disciplina: segurança em redes aplicada à saúde.": "Artigo escolhido: An Analysis of Pre-trained Models to Identify Cybersecurity Incidents Entities in the Healthcare Industry.",
            "[EDITAR] evidência ou exemplo": "Contexto: incidentes cibernéticos na área da saúde exigem a identificação de organizações, ações, vulnerabilidades e localidades.",
            "O artigo usa NER para localizar entidades em incidentes cibernéticos.": "Contexto: incidentes cibernéticos na área da saúde exigem a identificação de organizações, ações, vulnerabilidades e localidades.",
            "Tema da disciplina: segurança em redes aplicada à saúde; uso de NER em incidentes cibernéticos.": "Contexto: incidentes cibernéticos na área da saúde exigem a identificação de organizações, ações, vulnerabilidades e localidades.",
            "[EDITAR] implicação para a aula": "Relevância: o artigo aplica modelos de NER pré-treinados a textos especializados de segurança cibernética.",
            "Escolhemos porque permite discutir modelos, dados, métricas e replicabilidade.": "Relevância: o artigo aplica modelos de NER pré-treinados a textos especializados de segurança cibernética.",
        },
        "slide5.xml": {
            "02 [EDITAR] ": "01 ",
            "NOME DA SEÇÃO": "ARTIGO E REPRODUÇÃO",
        },
        "slide12.xml": {
            "REFERÊNCIAS": "REFERÊNCIAS",
            "[EDITAR] SOBRENOME, Nome. Título da obra. Local: Editora, ano.": "HUGGING FACE. CyberPeace-Institute/SecureBERT-NER. [S. l.], [s. d.]. Disponível em: https://huggingface.co/CyberPeace-Institute/SecureBERT-NER. Acesso em: 30 ago. 2026.",
            "[EDITAR] SOBRENOME, Nome. Título do artigo. Revista, v. 0, n. 0, ano.": "HUGGING FACE. Cyber-ThreaD/SecureBERT-APTNER. [S. l.], [s. d.]. Disponível em: https://huggingface.co/Cyber-ThreaD/SecureBERT-APTNER. Acesso em: 30 ago. 2026.",
            "[EDITAR] INSTITUIÇÃO. Título da página. Disponível em: <URL>. Acesso em: dia mês ano.": "PAIM, Rafael; IGNACZAK, Luciano. An analysis of pre-trained models to identify cybersecurity incidents entities in the healthcare industry. In: WORKSHOP DE TRABALHOS DE INICIAÇÃO CIENTÍFICA E DE GRADUAÇÃO - SIMPÓSIO BRASILEIRO DE CIBERSEGURANÇA (SBSEG), 25., 2025, Foz do Iguaçu, PR. Anais [...]. Porto Alegre: Sociedade Brasileira de Computação, 2025. p. 135-146. DOI: https://doi.org/10.5753/sbseg_estendido.2025.10726. Acesso em: 30 ago. 2026.",
            "[EDITAR] AUTOR ou INSTITUIÇÃO. Título do material. Ano.": "RODRIGUES, Gabriel; MACHADO, Gabriel; RESPLANDES, Angelo. healthcare_cyber_hybrid_1066.csv. [S. l.], 2026. Base de dados própria, em formato CSV.",
            "GRUPO DE REPRODUÇÃO. healthcare_cyber_v10_hybrid_1066.csv. [S. l.], 2026. Base de dados em formato CSV.": "RODRIGUES, Gabriel; MACHADO, Gabriel; RESPLANDES, Angelo. healthcare_cyber_hybrid_1066.csv. [S. l.], 2026. Base de dados própria, em formato CSV.",
            "Base do grupo: healthcare_cyber_v10_hybrid_1066.csv": "RODRIGUES, Gabriel; MACHADO, Gabriel; RESPLANDES, Angelo. healthcare_cyber_hybrid_1066.csv. [S. l.], 2026. Base de dados própria, em formato CSV.",
            "RODRIGUES, Gabriel; MACHADO, Gabriel. healthcare_cyber_v10_hybrid_1066.csv. [S. l.], 2026. Base de dados própria, em formato CSV.": "RODRIGUES, Gabriel; MACHADO, Gabriel; RESPLANDES, Angelo. healthcare_cyber_hybrid_1066.csv. [S. l.], 2026. Base de dados própria, em formato CSV.",
            "RODRIGUES, Gabriel; MACHADO, Gabriel. healthcare_cyber_hybrid_1066.csv. [S. l.], 2026. Base de dados própria, em formato CSV.": "RODRIGUES, Gabriel; MACHADO, Gabriel; RESPLANDES, Angelo. healthcare_cyber_hybrid_1066.csv. [S. l.], 2026. Base de dados própria, em formato CSV.",
        },
        "slide6.xml": {
            "[EDITAR] TÍTULO DO TÓPICO": "METODOLOGIA REPORTADA",
            "[EDITAR] ideia principal": "Coleta: 24.108 registros entre 01/01 e 30/10/2023.",
            "[EDITAR] evidência ou exemplo": "Filtragem: 15.705 links únicos, 1.449 portais e 1.039 notícias.",
            "[EDITAR] implicação para a aula": "Avaliação: 60 notícias, 400 tokens, 4 entidades; dois modelos SecureBERT.",
        },
        "slide7.xml": {
            "[EDITAR] TÍTULO DO TÓPICO": "BASE | DADOS ENCONTRADOS",
            "BASE V10 | DADOS ENCONTRADOS": "BASE | DADOS ENCONTRADOS",
            "[EDITAR] ideia principal": "1.066 registros: 702 notícias e 364 registros estruturados.",
            "[EDITAR] evidência ou exemplo": "Fontes: Becker's, HIPAA Journal, JD Supra, HHS OCR e Security Magazine.",
            "[EDITAR] implicação para a aula": "A base foi ampliada e ainda precisa de limpeza e deduplicação.",
        },
        "slide8.xml": {
            "[EDITAR] TÍTULO DO TÓPICO": "LIMITAÇÕES DA REPRODUÇÃO",
            "[EDITAR] ideia principal": "Corpus e anotações originais não estão disponíveis publicamente.",
            "[EDITAR] evidência ou exemplo": "Os critérios completos de coleta, seleção e deduplicação não foram publicados.",
            "[EDITAR] implicação para a aula": "A base expandida não é idêntica; os resultados provavelmente serão diferentes.",
        },
        "slide10.xml": {
            "[EDITAR] TÍTULO DO TÓPICO": "PLANEJAMENTO DE REPRODUÇÃO",
            "PLANO DE REPRODUÇÃO": "PLANEJAMENTO DE REPRODUÇÃO",
            "[EDITAR] ideia principal": "Separar notícias dos registros estruturados e finalizar a limpeza.",
            "[EDITAR] evidência ou exemplo": "Executar os dois modelos e avaliar com as métricas Strict e Partial.",
            "[EDITAR] implicação para a aula": "Registrar versões, desvios e resultados como reprodução aproximada.",
        },
        "slide11.xml": {
            "[EDITAR] TÍTULO DO TÓPICO": "PROBLEMÁTICA E OBJETIVOS",
            "CRONOGRAMA DOS MARCOS": "PROBLEMÁTICA E OBJETIVOS",
            "[EDITAR] ideia principal": "Problemática: modelos de NER pré-treinados precisam ser avaliados em textos de segurança cibernética da área da saúde.",
            "1º marco: equipe e artigo; apresentado junto nesta entrega.": "Problemática: modelos de NER pré-treinados precisam ser avaliados em textos de segurança cibernética da área da saúde.",
            "[EDITAR] evidência ou exemplo": "Objetivo do artigo: identificar entidades de incidentes cibernéticos usando modelos pré-treinados.",
            "31/08: 2º marco, contexto, metodologia e planejamento.": "Objetivo do artigo: identificar entidades de incidentes cibernéticos usando modelos pré-treinados.",
            "[EDITAR] implicação para a aula": "Objetivo da reprodução: reconstruir o método, comparar os modelos e avaliar os resultados.",
            "28/09, 19/10 e 23/11: resultados parciais, finais e resumo expandido.": "Objetivo da reprodução: reconstruir o método, comparar os modelos e avaliar os resultados.",
        },
        "slide9.xml": {
            "02 [EDITAR] ": "02 ",
            "NOME DA SEÇÃO": "PLANEJAMENTO",
        },
    }

    for name, mapping in replacements.items():
        path = slides_dir / name
        document = load_document(path)
        apply_common_footer(document)
        replace_texts(document, mapping)
        if name == "slide12.xml":
            format_reference_list(document)
        if name == "slide6.xml":
            format_methodology_list(document)
        if name == "slide1.xml":
            fit_cover_authors(document)
        set_bullet_sequence(document)
        remove_edit_markers(document)
        write_document(path, document)


def reorder_presentation(unpacked_dir: Path) -> None:
    """Reorder slide references and update visible page numbers in an unpacked deck."""

    presentation_path = unpacked_dir / "ppt" / "presentation.xml"
    rels_path = unpacked_dir / "ppt" / "_rels" / "presentation.xml.rels"
    presentation = load_document(presentation_path)
    rels = load_document(rels_path)

    target_by_rid = {
        node.getAttribute("Id"): node.getAttribute("Target")
        for node in rels.getElementsByTagName("Relationship")
        if node.getAttribute("Target").startswith("slides/")
    }
    item_by_slide = {}
    rid_by_slide = {}
    slide_ids = presentation.getElementsByTagName("p:sldIdLst")[0]
    for node in slide_ids.getElementsByTagName("p:sldId"):
        target = target_by_rid.get(node.getAttribute("r:id"), "")
        if target:
            item_by_slide[Path(target).name] = node.cloneNode(deep=True)
    for rid, target in target_by_rid.items():
        rid_by_slide[Path(target).name] = rid

    order = [
        "slide1.xml",
        "slide2.xml",
        "slide3.xml",
        "slide4.xml",
        "slide5.xml",
        "slide11.xml",
        "slide6.xml",
        "slide7.xml",
        "slide8.xml",
        "slide9.xml",
        "slide10.xml",
        "slide12.xml",
    ]
    for child in list(slide_ids.childNodes):
        slide_ids.removeChild(child)
    next_id = (
        max(
            int(node.getAttribute("id"))
            for node in item_by_slide.values()
            if node.getAttribute("id").isdigit()
        )
        + 1
    )
    for name in order:
        item = item_by_slide.get(name)
        if item is None:
            item = presentation.createElementNS(PRESENTATION_NS, "p:sldId")
            item.setAttribute("id", str(next_id))
            item.setAttributeNS(RELATIONSHIP_NS, "r:id", rid_by_slide[name])
            next_id += 1
        slide_ids.appendChild(item)
        slide_ids.appendChild(presentation.createTextNode("\n"))
    write_document(presentation_path, presentation)

    for page, name in enumerate(order, start=1):
        path = unpacked_dir / "ppt" / "slides" / name
        document = load_document(path)
        set_footer_page(document, f"{page:02d}")
        write_document(path, document)


def main() -> int:
    """Edit and reorder an unpacked presentation directory from the CLI."""

    if len(sys.argv) != 2:
        print("Usage: update_template_deck.py <unpacked_dir>", file=sys.stderr)
        return 2
    unpacked_dir = Path(sys.argv[1])
    slides_dir = unpacked_dir / "ppt" / "slides"
    edit_slides(slides_dir)
    reorder_presentation(unpacked_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
