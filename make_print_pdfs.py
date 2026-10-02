"""Create individual, print-ready player packs from generated Markdown files."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)


INK = colors.HexColor("#22333B")
GREEN = colors.HexColor("#275B52")
RED = colors.HexColor("#963F45")
BRASS = colors.HexColor("#B28B47")
PALE = colors.HexColor("#F3F5F2")
MUTED = colors.HexColor("#667477")
RULE = colors.HexColor("#D7DDD8")

SPANISH_LABELS = {
    "running_header": "ARCHIVO DE LA MANSIÓN",
    "player_copy": "COPIA PERSONAL",
    "private_notice": "FICHA PRIVADA · SOLO PARA SU JUGADOR",
    "act_ii_notice": "ACTO II · ENTREGAR AL COMENZAR ESTA FASE",
    "common_copy": "MATERIAL COMÚN · UNA COPIA PARA CADA JUGADOR",
    "act_ii_short": "ACTO II",
    "page": "PÁGINA",
    "readme_title": "PDFs listos para imprimir",
    "pack_explanation": "Cada PDF de jugador incluye una copia completa del material común seguida únicamente de su ficha privada.",
    "act_ii_explanation": "Cada jugador tiene además un PDF independiente de Acto II. No lo entregues hasta que comience esa fase.",
    "solution_warning": "La solución del facilitador no se incluye en ningún PDF de jugador.",
}
ENGLISH_LABELS = {
    "running_header": "MANSION CASE FILE",
    "player_copy": "PERSONAL COPY",
    "private_notice": "PRIVATE ROLE · FOR THIS PLAYER ONLY",
    "act_ii_notice": "ACT II · DISTRIBUTE WHEN THIS PHASE BEGINS",
    "common_copy": "SHARED MATERIAL · ONE COPY PER PLAYER",
    "act_ii_short": "ACT II",
    "page": "PAGE",
    "readme_title": "Print-ready PDFs",
    "pack_explanation": "Each player PDF includes a full copy of the shared material followed only by that player's private role.",
    "act_ii_explanation": "Each player also has a separate Act II PDF. Do not distribute it until that phase begins.",
    "solution_warning": "The facilitator solution is not included in any player PDF.",
}


@dataclass(frozen=True)
class PlayerFiles:
    packet_path: Path
    stem: str
    player_name: str


def _register_fonts() -> tuple[str, str, str, str]:
    if "DossierSerif" in pdfmetrics.getRegisteredFontNames():
        return "DossierSerif", "DossierSerif-Bold", "DossierSans", "DossierMono"
    font_candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ),
        (
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
        ),
    ]
    for regular, bold, sans, mono in font_candidates:
        if all(Path(font_path).is_file() for font_path in (regular, bold, sans, mono)):
            pdfmetrics.registerFont(TTFont("DossierSerif", regular))
            pdfmetrics.registerFont(TTFont("DossierSerif-Bold", bold))
            pdfmetrics.registerFont(TTFont("DossierSans", sans))
            pdfmetrics.registerFont(TTFont("DossierMono", mono))
            return "DossierSerif", "DossierSerif-Bold", "DossierSans", "DossierMono"
    return "Times-Roman", "Times-Bold", "Helvetica", "Courier"


def _language_labels(language: str, common_markdown: str) -> dict[str, str]:
    if language.casefold() == "auto":
        language = "Spanish" if "Cómo jugar" in common_markdown or "La víctima" in common_markdown else "English"
    return SPANISH_LABELS if language.casefold() in {"spanish", "es", "español"} else ENGLISH_LABELS


def _inline_markup(text: str) -> str:
    safe_text = escape(text)
    safe_text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe_text)
    safe_text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", safe_text)
    safe_text = re.sub(r"`([^`]+)`", r"<font name='DossierMono'>\1</font>", safe_text)
    return safe_text


def _make_styles() -> dict[str, ParagraphStyle]:
    serif, serif_bold, sans, _ = _register_fonts()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DossierTitle",
            parent=base["Title"],
            fontName=serif_bold,
            fontSize=22,
            leading=27,
            textColor=GREEN,
            alignment=TA_LEFT,
            spaceBefore=2 * mm,
            spaceAfter=4 * mm,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "DossierH2",
            parent=base["Heading2"],
            fontName=serif_bold,
            fontSize=15,
            leading=19,
            textColor=GREEN,
            backColor=PALE,
            borderColor=BRASS,
            borderWidth=0.7,
            borderPadding=(5, 7, 5, 8),
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "DossierH3",
            parent=base["Heading3"],
            fontName=serif_bold,
            fontSize=11.5,
            leading=15,
            textColor=RED,
            spaceBefore=3 * mm,
            spaceAfter=1.5 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "DossierBody",
            parent=base["BodyText"],
            fontName=sans,
            fontSize=9.4,
            leading=14,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=3 * mm,
            splitLongWords=True,
            allowWidows=0,
            allowOrphans=0,
        ),
        "bullet": ParagraphStyle(
            "DossierBullet",
            parent=base["BodyText"],
            fontName=sans,
            fontSize=9.2,
            leading=13.5,
            leftIndent=5 * mm,
            firstLineIndent=-4 * mm,
            textColor=INK,
            spaceAfter=2.5 * mm,
            allowWidows=0,
            allowOrphans=0,
        ),
        "notice": ParagraphStyle(
            "DossierNotice",
            parent=base["BodyText"],
            fontName=sans,
            fontSize=8,
            leading=11,
            textColor=RED,
            alignment=TA_CENTER,
            borderColor=RED,
            borderWidth=0.8,
            borderPadding=7,
            spaceBefore=2 * mm,
            spaceAfter=6 * mm,
        ),
        "small": ParagraphStyle(
            "DossierSmall",
            parent=base["BodyText"],
            fontName=sans,
            fontSize=8,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
    }


class AccentRule(Flowable):
    def __init__(self, width: float = 100 * mm, height: float = 5 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        self.width = available_width
        return self.width, self.height

    def draw(self) -> None:
        self.canv.setStrokeColor(BRASS)
        self.canv.setLineWidth(1.2)
        self.canv.line(0, self.height / 2, self.width, self.height / 2)
        self.canv.setFillColor(RED)
        self.canv.circle(self.width / 2, self.height / 2, 1.2 * mm, fill=1, stroke=0)


class DossierDocTemplate(BaseDocTemplate):
    def __init__(
        self,
        filename: Path,
        title: str,
        copy_label: str,
        labels: dict[str, str],
        pagesize: tuple[float, float],
    ):
        self.dossier_title = title
        self.copy_label = copy_label
        self.labels = labels
        page_width, page_height = pagesize
        left = 20 * mm
        right = 20 * mm
        top = 23 * mm
        bottom = 19 * mm
        super().__init__(
            str(filename),
            pagesize=pagesize,
            leftMargin=left,
            rightMargin=right,
            topMargin=top,
            bottomMargin=bottom,
            title=title,
            author="Mystery Murder Game Generator",
            pageCompression=1,
        )
        frame = Frame(left, bottom, page_width - left - right, page_height - top - bottom, id="main")
        self.addPageTemplates(PageTemplate(id="dossier", frames=frame, onPage=self._draw_page_furniture))

    def _draw_page_furniture(self, canvas, document) -> None:
        page_width, page_height = self.pagesize
        canvas.saveState()
        canvas.setFillColor(GREEN)
        canvas.rect(0, page_height - 5 * mm, page_width, 5 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(BRASS)
        canvas.setLineWidth(0.65)
        canvas.line(20 * mm, page_height - 15 * mm, page_width - 20 * mm, page_height - 15 * mm)
        canvas.setFont("DossierSans", 7.4)
        canvas.setFillColor(GREEN)
        canvas.drawString(20 * mm, page_height - 12.5 * mm, self.labels["running_header"])
        canvas.setFillColor(MUTED)
        canvas.drawRightString(page_width - 20 * mm, page_height - 12.5 * mm, self.copy_label)
        canvas.setStrokeColor(RULE)
        canvas.line(20 * mm, 14 * mm, page_width - 20 * mm, 14 * mm)
        canvas.setFont("DossierSans", 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 9.5 * mm, self.dossier_title[:64])
        canvas.drawRightString(page_width - 20 * mm, 9.5 * mm, f"{self.labels['page']} {document.page}")
        canvas.restoreState()


def _markdown_flowables(markdown: str, styles: dict[str, ParagraphStyle], max_width: float) -> list[Flowable]:
    flowables: list[Flowable] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        content = " ".join(line.strip() for line in paragraph_lines)
        flowables.append(Paragraph(_inline_markup(content), styles["body"]))
        paragraph_lines.clear()

    for source_line in markdown.splitlines():
        line = source_line.strip()
        if not line:
            flush_paragraph()
            continue
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            style_name = {1: "title", 2: "h2", 3: "h3"}[level]
            heading = Paragraph(_inline_markup(heading_match.group(2)), styles[style_name])
            if level == 1:
                flowables.extend([heading, AccentRule(max_width), Spacer(1, 3 * mm)])
            else:
                flowables.append(KeepTogether([heading]))
            continue
        bullet_match = re.match(r"^-\s+(.+)$", line)
        if bullet_match:
            flush_paragraph()
            flowables.append(Paragraph(f"<font color='{RED.hexval()}'>&bull;</font> {_inline_markup(bullet_match.group(1))}", styles["bullet"]))
            continue
        paragraph_lines.append(line)
    flush_paragraph()
    return flowables


def _player_name(markdown: str, filename: Path) -> str:
    first_heading = re.search(r"^#\s+Ficha privada:\s*(.+)$", markdown, flags=re.MULTILINE)
    if first_heading:
        return first_heading.group(1).strip()
    return filename.stem


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "jugador"


def _write_pdf(
    destination: Path,
    sections: Iterable[tuple[str, str]],
    title: str,
    copy_label: str,
    labels: dict[str, str],
    pagesize: tuple[float, float],
) -> None:
    styles = _make_styles()
    doc = DossierDocTemplate(destination, title, copy_label, labels, pagesize)
    usable_width = pagesize[0] - doc.leftMargin - doc.rightMargin
    story: list[Flowable] = []
    sections = list(sections)
    for index, (kind, markdown) in enumerate(sections):
        if index:
            story.append(PageBreak())
        if kind == "private":
            story.append(Paragraph(escape(labels["private_notice"]), styles["notice"]))
        elif kind == "act_ii":
            story.append(Paragraph(escape(labels["act_ii_notice"]), styles["notice"]))
        story.extend(_markdown_flowables(markdown, styles, usable_width))
    doc.build(story)


def build_print_pdfs(
    input_dir: str | Path = "output",
    output_dir: str | Path | None = None,
    language: str = "auto",
    paper: str = "A4",
) -> dict[str, list[Path]]:
    source = Path(input_dir)
    packets_dir = source / "player_packets"
    common_path = source / "player_handout.md"
    act_two_path = source / "act_ii_reveal.md"
    if not common_path.is_file():
        raise FileNotFoundError(f"Missing shared handout: {common_path}")
    if not act_two_path.is_file():
        raise FileNotFoundError(f"Missing Act II reveal: {act_two_path}")
    if not packets_dir.is_dir():
        raise FileNotFoundError(f"Missing player packets directory: {packets_dir}")

    common_markdown = common_path.read_text(encoding="utf-8")
    act_two_markdown = act_two_path.read_text(encoding="utf-8")
    labels = _language_labels(language, common_markdown)
    packet_sources = sorted(packets_dir.glob("*.md"))
    if not packet_sources:
        raise ValueError(f"No player packet Markdown files found in {packets_dir}")

    page_sizes = {"A4": A4, "LETTER": LETTER}
    normalized_paper = paper.upper()
    if normalized_paper not in page_sizes:
        raise ValueError("paper must be A4 or Letter")
    pagesize = page_sizes[normalized_paper]

    destination = Path(output_dir) if output_dir is not None else source / "print-ready"
    player_output = destination / "players"
    act_two_output = destination / "act-ii"
    player_output.mkdir(parents=True, exist_ok=True)
    act_two_output.mkdir(parents=True, exist_ok=True)

    player_pdfs: list[Path] = []
    act_two_pdfs: list[Path] = []
    player_files: list[PlayerFiles] = []
    for packet_path in packet_sources:
        packet_markdown = packet_path.read_text(encoding="utf-8")
        player_name = _player_name(packet_markdown, packet_path)
        stem = packet_path.stem
        player_files.append(PlayerFiles(packet_path, stem, player_name))

        pack_path = player_output / f"{stem}-paquete.pdf"
        _write_pdf(
            pack_path,
            [("shared", common_markdown), ("private", packet_markdown)],
            title=f"{player_name} · {labels['player_copy']}",
            copy_label=f"{labels['player_copy']} · {player_name}",
            labels=labels,
            pagesize=pagesize,
        )
        player_pdfs.append(pack_path)

        act_two_path_for_player = act_two_output / f"{stem}-acto-ii.pdf"
        _write_pdf(
            act_two_path_for_player,
            [("act_ii", act_two_markdown)],
            title=f"{player_name} · Acto II",
            copy_label=f"{labels['act_ii_short']} · {player_name}",
            labels=labels,
            pagesize=pagesize,
        )
        act_two_pdfs.append(act_two_path_for_player)

    index_path = destination / "INSTRUCCIONES-DE-IMPRESION.md"
    index_lines = [
        f"# {labels['readme_title']}",
        "",
        labels["common_copy"],
        labels["pack_explanation"],
        labels["act_ii_explanation"],
        labels["solution_warning"],
        "",
        f"Jugadores: {len(player_files)}",
        f"Copias necesarias de la hoja común: {len(player_files)}",
        f"Copias necesarias de las pistas del Acto II: {len(player_files)}",
        "",
        "## Paquetes iniciales",
        *[f"- `{path.relative_to(destination).as_posix()}` · {player.player_name}" for path, player in zip(player_pdfs, player_files)],
        "",
        "## Sobres de Acto II",
        *[f"- `{path.relative_to(destination).as_posix()}` · {player.player_name}" for path, player in zip(act_two_pdfs, player_files)],
        "",
    ]
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    return {"players": player_pdfs, "act_ii": act_two_pdfs, "index": [index_path]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("output"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--language", choices=["auto", "Spanish", "English"], default="auto")
    parser.add_argument("--paper", choices=["A4", "Letter"], default="A4")
    args = parser.parse_args()

    outputs = build_print_pdfs(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        language=args.language,
        paper=args.paper,
    )
    print(f"PDFs creados para {len(outputs['players'])} jugadores.")
    print(f"Paquetes completos por jugador: {args.output_dir or args.input_dir / 'print-ready'}/players")
    print(f"Sobres separados de Acto II: {args.output_dir or args.input_dir / 'print-ready'}/act-ii")
    print(f"Índice de impresión: {outputs['index'][0]}")


if __name__ == "__main__":
    main()
