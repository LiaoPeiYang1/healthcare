from pathlib import Path
from uuid import uuid4

from app.config import settings


class LocalStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.storage_path
        self.root.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        full_path = self.root / key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def write_bytes(self, key: str, content: bytes) -> str:
        self._full_path(key).write_bytes(content)
        return key

    def read_bytes(self, key: str) -> bytes:
        return self._full_path(key).read_bytes()

    def delete(self, key: str | None) -> None:
        if not key:
            return
        path = self._full_path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._full_path(key).exists()

    def chunk_key(self, file_hash: str, chunk_index: int) -> str:
        return f'chunks/{file_hash}/{chunk_index}.part'

    def save_chunk(self, file_hash: str, chunk_index: int, content: bytes) -> str:
        key = self.chunk_key(file_hash, chunk_index)
        self.write_bytes(key, content)
        return key

    def merge_chunks(self, file_hash: str, total_chunks: int, suffix: str) -> str:
        merged_key = f'originals/{uuid4()}{suffix}'
        merged_path = self._full_path(merged_key)
        with merged_path.open('wb') as target:
            for index in range(total_chunks):
                chunk_path = self._full_path(self.chunk_key(file_hash, index))
                target.write(chunk_path.read_bytes())
        return merged_key

    def cleanup_chunks(self, file_hash: str, total_chunks: int) -> None:
        for index in range(total_chunks):
            key = self.chunk_key(file_hash, index)
            path = self._full_path(key)
            if path.exists():
                path.unlink()

    def build_pdf_bytes(self, title: str, body: str) -> bytes:
        safe_title = title.replace('(', '[').replace(')', ']')
        safe_body = body.replace('(', '[').replace(')', ']').replace('\n', ' ')
        stream = f'BT /F1 18 Tf 50 760 Td ({safe_title}) Tj 0 -28 Td /F1 12 Tf ({safe_body[:180]}) Tj ET'
        pdf = (
            '%PDF-1.4\n'
            '1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n'
            '2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n'
            '3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R >> endobj\n'
            f'4 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj\n'
            'xref\n0 5\n0000000000 65535 f \n'
            '0000000010 00000 n \n0000000062 00000 n \n0000000119 00000 n \n0000000207 00000 n \n'
            'trailer << /Root 1 0 R /Size 5 >>\nstartxref\n320\n%%EOF\n'
        )
        return pdf.encode('utf-8')

    def save_result_pdf(self, title: str, body: str, category: str = 'results') -> str:
        key = f'{category}/{uuid4()}.pdf'
        self.write_bytes(key, self.build_pdf_bytes(title, body))
        return key

    def save_pdf_bytes(self, content: bytes, category: str = 'results') -> str:
        key = f'{category}/{uuid4()}.pdf'
        self.write_bytes(key, content)
        return key


storage = LocalStorage()
