const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Healthcare Cybersecurity NER Reproduction";
pptx.company = "UNIFESSPA";
pptx.subject = "2º marco da reprodução do artigo";
pptx.title = "Aula 31 | Contexto e metodologia da reprodução";
pptx.lang = "pt-BR";
pptx.theme = {
  headFontFace: "Trebuchet MS",
  bodyFontFace: "Aptos",
  lang: "pt-BR",
};

const C = {
  plum: "35132F",
  plum2: "5C1B4D",
  cream: "F8F2E9",
  white: "FFFDF9",
  coral: "D26991",
  peach: "F1D4C6",
  mint: "A7D8C8",
  green: "2A7C6F",
  text: "3D3440",
  muted: "756A74",
  line: "E5D8D0",
};

const S = pptx.ShapeType;
const slide = pptx.addSlide();
slide.background = { color: C.cream };

function addRect(x, y, w, h, fill, radius = false, line = null) {
  slide.addShape(radius ? S.roundRect : S.rect, {
    x,
    y,
    w,
    h,
    rectRadius: radius ? 0.08 : undefined,
    fill: { color: fill },
    line: line ? { color: line, width: 1 } : { color: fill, transparency: 100 },
  });
}

function addText(text, x, y, w, h, options = {}) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    margin: 0,
    fontFace: options.fontFace || "Aptos",
    fontSize: options.fontSize || 14,
    color: options.color || C.text,
    bold: options.bold || false,
    italic: options.italic || false,
    breakLine: false,
    align: options.align || "left",
    valign: options.valign || "top",
    fit: "shrink",
    paraSpaceAfterPt: options.paraSpaceAfterPt || 0,
    charSpacing: options.charSpacing || 0,
  });
}

// Left rail
addRect(0, 0, 2.35, 7.5, C.plum);
addText("REPRODUÇÃO\nDO ARTIGO", 0.38, 0.48, 1.55, 0.48, {
  fontSize: 10,
  color: C.mint,
  bold: true,
  charSpacing: 1.2,
});
addText("AULA\n31", 0.35, 1.24, 1.65, 1.35, {
  fontFace: "Trebuchet MS",
  fontSize: 36,
  color: C.white,
  bold: true,
});
addRect(0.38, 2.82, 0.65, 0.06, C.coral);
addText("31/08/2026", 0.38, 3.06, 1.55, 0.3, {
  fontSize: 14,
  color: C.white,
  bold: true,
});
addText("2º MARCO", 0.38, 3.45, 1.55, 0.24, {
  fontSize: 10,
  color: C.mint,
  bold: true,
  charSpacing: 1.2,
});
addText("Contexto,\nmetodologia e\nplanejamento", 0.38, 3.84, 1.55, 0.9, {
  fontSize: 15,
  color: C.white,
  bold: true,
});
addRect(0.38, 5.45, 1.55, 0.02, "8A4C79");
addText("24/08/2026", 0.38, 5.73, 1.5, 0.22, {
  fontSize: 10,
  color: C.mint,
  bold: true,
});
addText("Não houve aula", 0.38, 6.02, 1.55, 0.24, {
  fontSize: 13,
  color: C.white,
});
addText("UNIFESSPA", 0.38, 7.1, 1.55, 0.18, {
  fontSize: 9,
  color: "CDB5C7",
  bold: true,
  charSpacing: 1.2,
});

// Main heading
addText("Contexto e metodologia da reprodução", 2.75, 0.45, 8.0, 0.44, {
  fontFace: "Trebuchet MS",
  fontSize: 25,
  color: C.plum,
  bold: true,
});
addText("Do artigo publicado a uma base que conseguimos auditar", 2.75, 0.98, 7.5, 0.25, {
  fontSize: 13,
  color: C.muted,
  italic: true,
});
addText("2º MARCO", 11.6, 0.52, 1.0, 0.2, {
  fontSize: 10,
  color: C.coral,
  bold: true,
  align: "right",
  charSpacing: 1.1,
});

// Problem and objective cards
addRect(2.75, 1.48, 4.25, 1.15, C.white, true, C.line);
addRect(2.75, 1.48, 0.09, 1.15, C.coral);
addText("PROBLEMA", 3.02, 1.67, 1.6, 0.18, {
  fontSize: 10,
  color: C.coral,
  bold: true,
  charSpacing: 1.1,
});
addText("O corpus original (1.039 notícias) e as anotações manuais não foram publicados.", 3.02, 1.94, 3.67, 0.46, {
  fontSize: 13,
  color: C.text,
});

addRect(7.2, 1.48, 5.35, 1.15, C.plum2, true);
addText("OBJETIVO DA AULA", 7.48, 1.67, 2.0, 0.18, {
  fontSize: 10,
  color: C.mint,
  bold: true,
  charSpacing: 1.1,
});
addText("Apresentar contexto, objetivos, metodologia e o plano de validação da reprodução.", 7.48, 1.94, 4.72, 0.46, {
  fontSize: 13,
  color: C.white,
});

// Paper pipeline
addText("PIPELINE REPORTADO NO ARTIGO", 2.75, 2.96, 3.2, 0.18, {
  fontSize: 10,
  color: C.plum,
  bold: true,
  charSpacing: 1.1,
});
addText("números do artigo", 11.2, 2.96, 1.35, 0.18, {
  fontSize: 9,
  color: C.muted,
  italic: true,
  align: "right",
});

const pipeline = [
  ["24.108", "registros\ncoletados", C.plum],
  ["15.705", "links\núnicos", C.white],
  ["1.449", "portais\nselecionados", C.white],
  ["1.039", "notícias\nfinais", C.mint],
];
pipeline.forEach(([number, label, fill], index) => {
  const x = 2.75 + index * 2.48;
  addRect(x, 3.27, 2.28, 0.92, fill, true, fill === C.white ? C.line : null);
  addText(number, x + 0.18, 3.43, 1.92, 0.28, {
    fontFace: "Trebuchet MS",
    fontSize: 22,
    color: fill === C.white ? C.plum : C.white,
    bold: true,
    align: "center",
  });
  addText(label, x + 0.18, 3.76, 1.92, 0.28, {
    fontSize: 10,
    color: fill === C.white ? C.muted : C.cream,
    bold: true,
    align: "center",
  });
});

// Current data snapshot
addRect(2.75, 4.54, 6.08, 1.62, C.white, true, C.line);
addText("BASE V10 | LEVANTAMENTO ATUAL", 3.02, 4.76, 3.5, 0.18, {
  fontSize: 10,
  color: C.green,
  bold: true,
  charSpacing: 1.05,
});
addText("1.066", 3.02, 5.08, 1.35, 0.38, {
  fontFace: "Trebuchet MS",
  fontSize: 28,
  color: C.plum,
  bold: true,
});
addText("registros totais", 3.04, 5.51, 1.5, 0.16, {
  fontSize: 10,
  color: C.muted,
});
addRect(4.74, 5.06, 0.02, 0.82, C.line);
addText("702", 5.04, 5.08, 0.9, 0.32, {
  fontFace: "Trebuchet MS",
  fontSize: 23,
  color: C.green,
  bold: true,
});
addText("notícias", 5.06, 5.51, 1.0, 0.16, {
  fontSize: 10,
  color: C.muted,
});
addRect(6.27, 5.06, 0.02, 0.82, C.line);
addText("364", 6.58, 5.08, 1.0, 0.32, {
  fontFace: "Trebuchet MS",
  fontSize: 23,
  color: C.coral,
  bold: true,
});
addText("registros estruturados", 6.58, 5.51, 1.65, 0.16, {
  fontSize: 10,
  color: C.muted,
});
addText("Base híbrida; ainda requer limpeza, deduplicação e validação antes da avaliação final.", 3.02, 5.86, 5.45, 0.18, {
  fontSize: 9.5,
  color: C.muted,
  italic: true,
});

// Source composition bars
addRect(9.08, 4.54, 3.47, 1.62, C.plum, true);
addText("FONTES NA BASE V10", 9.35, 4.76, 2.8, 0.18, {
  fontSize: 10,
  color: C.mint,
  bold: true,
  charSpacing: 1.05,
});
const sources = [
  ["Becker's", 531, C.coral],
  ["HIPAA", 264, C.mint],
  ["JD Supra", 149, "E8B56F"],
  ["HHS OCR", 100, "D9B1CB"],
  ["Security", 22, "B5A0B2"],
];
sources.forEach(([label, value, color], index) => {
  const y = 5.04 + index * 0.19;
  addText(label, 9.35, y, 0.82, 0.14, {
    fontSize: 8.5,
    color: C.white,
  });
  addRect(10.2, y + 0.025, 1.45, 0.09, "754268");
  addRect(10.2, y + 0.025, 1.45 * (value / 531), 0.09, color);
  addText(String(value), 11.82, y - 0.01, 0.42, 0.14, {
    fontSize: 8.5,
    color: C.white,
    bold: true,
    align: "right",
  });
});

// Footer status
addRect(2.75, 6.52, 9.8, 0.56, C.peach, true);
addText("STATUS", 3.02, 6.72, 0.7, 0.16, {
  fontSize: 9.5,
  color: C.plum,
  bold: true,
  charSpacing: 1,
});
addText("reprodução aproximada  |  CSV: healthcare_cyber_v10_hybrid_1066.csv  |  leitura preliminar", 3.86, 6.72, 8.35, 0.16, {
  fontSize: 10,
  color: C.plum,
});

pptx.writeFile({ fileName: "slides/aula-31-2-marco.pptx" });
