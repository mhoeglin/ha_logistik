"""Label sheet generation (A4) with QR + Code128 barcode + human-readable text.

Each label carries the same payload in both a QR code and a Code128 1D
barcode (e.g. "LOC:000123"), plus a caption line. Labels are laid out on a
configurable grid on an A4 page, suitable for printing on adhesive label
sheets.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import code128
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


@dataclass(frozen=True)
class LabelSpec:
    """A single label's content."""

    payload: str  # e.g. "LOC:000123" -> encoded in QR and Code128
    caption: str  # human-readable line, e.g. "Keller Regal A"


@dataclass(frozen=True)
class SheetLayout:
    """A4 label grid layout. Defaults ~ 3x8 = 24 labels per sheet."""

    cols: int = 3
    rows: int = 8
    margin_x: float = 8 * mm
    margin_y: float = 10 * mm
    gap_x: float = 3 * mm
    gap_y: float = 2 * mm

    def cell_size(self) -> tuple[float, float]:
        page_w, page_h = A4
        usable_w = page_w - 2 * self.margin_x - (self.cols - 1) * self.gap_x
        usable_h = page_h - 2 * self.margin_y - (self.rows - 1) * self.gap_y
        return usable_w / self.cols, usable_h / self.rows

    def per_page(self) -> int:
        return self.cols * self.rows


def _draw_qr(c: canvas.Canvas, payload: str, x: float, y: float, size: float) -> None:
    widget = QrCodeWidget(payload)
    bounds = widget.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, x, y)


def _draw_label(
    c: canvas.Canvas,
    spec: LabelSpec,
    x: float,
    y: float,
    cell_w: float,
    cell_h: float,
) -> None:
    pad = 2 * mm
    qr_size = min(cell_h - 2 * pad, cell_w * 0.42)
    # QR on the left, vertically centred.
    qr_x = x + pad
    qr_y = y + (cell_h - qr_size) / 2
    _draw_qr(c, spec.payload, qr_x, qr_y, qr_size)

    text_x = qr_x + qr_size + pad
    # Caption + code text near the top of the cell.
    c.setFont("Helvetica-Bold", 8)
    c.drawString(text_x, y + cell_h - pad - 8, spec.caption[:24])
    c.setFont("Helvetica", 7)
    c.drawString(text_x, y + cell_h - pad - 18, spec.payload)

    # Code128 barcode below the caption, scaled to fit remaining width.
    avail_w = (x + cell_w - pad) - text_x
    if avail_w > 10 * mm:
        bar = code128.Code128(spec.payload, barHeight=8 * mm, humanReadable=False)
        # Scale horizontally to fit.
        scale = min(1.0, avail_w / bar.width) if bar.width else 1.0
        c.saveState()
        c.translate(text_x, y + pad + 2 * mm)
        c.scale(scale, 1.0)
        bar.drawOn(c, 0, 0)
        c.restoreState()


def render_label_sheet(
    labels: list[LabelSpec], layout: SheetLayout | None = None
) -> bytes:
    """Render labels onto one or more A4 pages; return PDF bytes."""
    layout = layout or SheetLayout()
    cell_w, cell_h = layout.cell_size()
    page_w, page_h = A4

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    per_page = layout.per_page()
    for idx, spec in enumerate(labels):
        pos = idx % per_page
        if idx > 0 and pos == 0:
            c.showPage()
        col = pos % layout.cols
        row = pos // layout.cols
        x = layout.margin_x + col * (cell_w + layout.gap_x)
        # Rows fill top-to-bottom; PDF origin is bottom-left.
        y = page_h - layout.margin_y - (row + 1) * cell_h - row * layout.gap_y
        _draw_label(c, spec, x, y, cell_w, cell_h)

    c.showPage()
    c.save()
    return buf.getvalue()


# --- Command codes ---------------------------------------------------------

# Only STORE is wired up in the workflow for now; the others are printed for
# future use (REMOVE/MOVE/LEND/RETURN) so the command sheet is complete.
COMMAND_LABELS: list[tuple[str, str]] = [
    ("STORE", "EINLAGERN"),
    ("REMOVE", "AUSLAGERN"),
    ("MOVE", "UMZUG"),
    ("LEND", "AUSLEIHEN"),
    ("RETURN", "ZURÜCKGEBEN"),
]


def command_label_specs() -> list[LabelSpec]:
    """LabelSpecs for the action command QR/1D codes (CMD:STORE, ...)."""
    from app.codes import format_command_code

    return [
        LabelSpec(payload=format_command_code(action), caption=caption)
        for action, caption in COMMAND_LABELS
    ]


def render_command_sheet() -> bytes:
    """Render the command codes onto a roomy A4 grid (2 columns)."""
    layout = SheetLayout(cols=2, rows=5)
    return render_label_sheet(command_label_specs(), layout)
