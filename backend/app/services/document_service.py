from io import BytesIO
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 36
MARGIN_Y = 44
LINE_HEIGHT = 16
COLUMN_GAP = 18
BODY_FONT = 'STSong-Light'
TITLE_FONT_SIZE = 16
BODY_FONT_SIZE = 10.5
HEADER_FONT_SIZE = 11
MAX_SECTION_CHARS = 1800

try:
    registerFont(UnicodeCIDFont(BODY_FONT))
except Exception:
    pass


class DocumentService:
    def build_sections_pdf(self, title: str, subtitle: str, sections: list[str]) -> bytes:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle(title)

        y = self._draw_title(pdf, f'{title} - {subtitle}')
        for index, section in enumerate(sections, start=1):
            header = f'第 {index} 段'
            y = self._ensure_space(pdf, y, 48)
            pdf.setFont(BODY_FONT, HEADER_FONT_SIZE)
            pdf.drawString(MARGIN_X, y, header)
            y -= 20
            y = self._draw_wrapped_text(
                pdf,
                section or '（该段未提取到可翻译文本）',
                MARGIN_X,
                y,
                PAGE_WIDTH - MARGIN_X * 2,
            )

        pdf.save()
        return buffer.getvalue()

    def extract_sections(self, path: Path) -> list[str]:
        suffix = path.suffix.lower()
        if suffix == '.pdf':
            return self._extract_pdf_sections(path)
        if suffix == '.docx':
            return self._extract_docx_sections(path)
        raise ValueError('仅支持 .docx 和 .pdf')

    def build_translation_pdf(self, title: str, sections: list[str]) -> bytes:
        return self.build_sections_pdf(title, '纯译文', sections)

    def build_source_pdf(self, title: str, sections: list[str]) -> bytes:
        return self.build_sections_pdf(title, '原文预览', sections)

    def build_bilingual_preview_pdf(
        self,
        title: str,
        source_sections: list[str],
        translated_sections: list[str],
    ) -> bytes:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle(f'{title} - 双语预览')

        left_x = MARGIN_X
        column_width = (PAGE_WIDTH - MARGIN_X * 2 - COLUMN_GAP) / 2
        right_x = left_x + column_width + COLUMN_GAP

        y = self._draw_title(pdf, f'{title} - 双语对照预览')
        for index, (source_text, translated_text) in enumerate(zip(source_sections, translated_sections), start=1):
            source_lines = self._split_lines(source_text or '（未提取到原文）', column_width)
            translated_lines = self._split_lines(translated_text or '（未生成译文）', column_width)
            page_no = 1

            while source_lines or translated_lines:
                y = self._ensure_space(pdf, y, 80)
                header = f'原页 {index}' if page_no == 1 else f'原页 {index}（续）'
                pdf.setFont(BODY_FONT, HEADER_FONT_SIZE)
                pdf.setFillColor(Color(0.13, 0.18, 0.28))
                pdf.drawString(left_x, y, f'{header} · 原文')
                pdf.drawString(right_x, y, f'{header} · 译文')
                pdf.setFillColor(Color(0, 0, 0))
                y -= 18

                available_lines = max(1, int((y - MARGIN_Y) / LINE_HEIGHT))
                left_batch = source_lines[:available_lines]
                right_batch = translated_lines[:available_lines]

                batch_length = max(len(left_batch), len(right_batch))
                source_lines = source_lines[batch_length:]
                translated_lines = translated_lines[batch_length:]

                draw_y = y
                for line_index in range(batch_length):
                    if draw_y < MARGIN_Y:
                        break
                    if line_index < len(left_batch):
                        pdf.setFont(BODY_FONT, BODY_FONT_SIZE)
                        pdf.drawString(left_x, draw_y, left_batch[line_index])
                    if line_index < len(right_batch):
                        pdf.setFont(BODY_FONT, BODY_FONT_SIZE)
                        pdf.drawString(right_x, draw_y, right_batch[line_index])
                    draw_y -= LINE_HEIGHT

                y = draw_y - 16
                page_no += 1
                if source_lines or translated_lines:
                    pdf.showPage()
                    y = PAGE_HEIGHT - MARGIN_Y

        pdf.save()
        return buffer.getvalue()

    def split_for_translation(self, section: str) -> list[str]:
        text = section.strip()
        if not text:
            return ['']

        chunks: list[str] = []
        current = ''
        for paragraph in text.splitlines():
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(current) + len(paragraph) + 1 <= MAX_SECTION_CHARS:
                current = f'{current}\n{paragraph}'.strip()
                continue
            if current:
                chunks.append(current)
            current = paragraph

        if current:
            chunks.append(current)
        return chunks or [text[:MAX_SECTION_CHARS]]

    def _extract_pdf_sections(self, path: Path) -> list[str]:
        reader = PdfReader(str(path))
        sections = []
        for page in reader.pages:
            text = (page.extract_text() or '').strip()
            if text:
                sections.append(text)
        if not sections:
            raise ValueError('文件未解析出可翻译文本')
        return sections

    def _extract_docx_sections(self, path: Path) -> list[str]:
        document = DocxDocument(str(path))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        if not paragraphs:
            raise ValueError('文件未解析出可翻译文本')

        sections: list[str] = []
        current = ''
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 1 <= MAX_SECTION_CHARS:
                current = f'{current}\n{paragraph}'.strip()
            else:
                if current:
                    sections.append(current)
                current = paragraph
        if current:
            sections.append(current)
        return sections

    def _draw_title(self, pdf: canvas.Canvas, title: str) -> float:
        y = PAGE_HEIGHT - MARGIN_Y
        pdf.setFont(BODY_FONT, TITLE_FONT_SIZE)
        pdf.drawString(MARGIN_X, y, title)
        return y - 28

    def _draw_wrapped_text(self, pdf: canvas.Canvas, text: str, x: float, y: float, width: float) -> float:
        for line in self._split_lines(text, width):
            y = self._ensure_space(pdf, y, LINE_HEIGHT)
            pdf.setFont(BODY_FONT, BODY_FONT_SIZE)
            pdf.drawString(x, y, line)
            y -= LINE_HEIGHT
        return y - 12

    def _split_lines(self, text: str, width: float) -> list[str]:
        lines: list[str] = []
        for paragraph in (text or '').splitlines() or ['']:
            paragraph = paragraph or ' '
            lines.extend(simpleSplit(paragraph, BODY_FONT, BODY_FONT_SIZE, width))
        return lines or [' ']

    def _ensure_space(self, pdf: canvas.Canvas, y: float, required_height: float) -> float:
        if y - required_height >= MARGIN_Y:
            return y
        pdf.showPage()
        return PAGE_HEIGHT - MARGIN_Y


document_service = DocumentService()
