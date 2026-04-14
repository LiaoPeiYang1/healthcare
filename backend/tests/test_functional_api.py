import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


class FunctionalApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ['DATABASE_URL'] = f"sqlite+aiosqlite:///{cls.temp_dir.name}/functional-test.db"
        os.environ['STORAGE_ROOT'] = f'{cls.temp_dir.name}/storage'
        os.environ['DASHSCOPE_API_KEY'] = ''
        os.environ['JWT_SECRET_KEY'] = 'functional-test-secret'

        from fastapi.testclient import TestClient

        from app.main import app
        from app.db.session import engine
        from app.services.translate_service import translate_service

        cls._original_enqueue_file_translation = translate_service.enqueue_file_translation
        translate_service.enqueue_file_translation = lambda task_id: None
        cls.engine = engine
        cls.translate_service = translate_service
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.translate_service.enqueue_file_translation = cls._original_enqueue_file_translation
        cls.client_context.__exit__(None, None, None)
        asyncio.run(cls.engine.dispose())
        cls.temp_dir.cleanup()

    def auth_headers(self) -> dict[str, str]:
        response = self.client.post(
            '/api/auth/login',
            json={'email': 'demo@example.com', 'password': 'Passw0rd1'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        token = response.json()['data']['tokens']['access_token']
        return {'Authorization': f'Bearer {token}'}

    def test_health_login_and_feishu_status(self) -> None:
        health = self.client.get('/health')
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {'status': 'ok'})

        login = self.client.post(
            '/api/auth/login',
            json={'email': 'demo@example.com', 'password': 'Passw0rd1'},
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(login.json()['data']['user']['email'], 'demo@example.com')
        self.assertIn('access_token', login.json()['data']['tokens'])

        feishu_status = self.client.get('/api/auth/feishu/status')
        self.assertEqual(feishu_status.status_code, 200)
        self.assertFalse(feishu_status.json()['data']['enabled'])

    def test_detect_language_supports_chinese_german_and_french(self) -> None:
        cases = [
            ('患者每日一次服用。', 'zh'),
            ('Der Patient nimmt das Arzneimittel ein.', 'de'),
            ('Le patient prend la dose prescrite.', 'fr'),
        ]
        for text, expected_lang in cases:
            with self.subTest(expected_lang=expected_lang):
                response = self.client.post('/api/detect', json={'text': text})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['data']['lang'], expected_lang)

    def test_text_translation_auto_detect_rejects_same_target_language(self) -> None:
        response = self.client.post(
            '/api/translate/text',
            headers=self.auth_headers(),
            json={
                'text': '患者每日一次服用。',
                'source_lang': 'auto',
                'target_lang': 'zh',
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], '源语言与目标语言不能相同')

    def test_text_translation_creates_history_and_enforces_length_limit(self) -> None:
        headers = self.auth_headers()
        translate = self.client.post(
            '/api/translate/text',
            headers=headers,
            json={
                'text': '患者每日一次服用。',
                'source_lang': 'auto',
                'target_lang': 'de',
            },
        )
        self.assertEqual(translate.status_code, 200, translate.text)
        payload = translate.json()['data']
        self.assertEqual(payload['source_lang'], 'zh')
        self.assertEqual(payload['terminology_count'], 0)
        self.assertIn('translated_text', payload)

        history = self.client.get(
            '/api/history?task_type=text&page=1&page_size=20',
            headers=headers,
        )
        self.assertEqual(history.status_code, 200, history.text)
        history_items = history.json()['data']['items']
        self.assertTrue(any(item['id'] == payload['history_id'] for item in history_items))

        too_long = self.client.post(
            '/api/translate/text',
            headers=headers,
            json={
                'text': '中' * 5001,
                'source_lang': 'auto',
                'target_lang': 'de',
            },
        )
        self.assertEqual(too_long.status_code, 422)

    def test_history_detail_is_isolated_by_current_user(self) -> None:
        headers = self.auth_headers()

        async def seed_other_user_history() -> tuple[str, str]:
            from app.core.security import create_access_token, hash_password
            from app.db.session import AsyncSessionLocal
            from app.models.history import History
            from app.models.translate_task import TranslateTask
            from app.models.user import User

            async with AsyncSessionLocal() as session:
                other_user = User(
                    email='other@example.com',
                    name='其他用户',
                    auth_type='password',
                    password_hash=hash_password('Passw0rd1'),
                    is_active=True,
                )
                session.add(other_user)
                await session.flush()

                now = datetime.now(timezone.utc)
                task = TranslateTask(
                    user_id=other_user.id,
                    task_type='text',
                    status='success',
                    source_lang='zh',
                    target_lang='en',
                    source_text='其他用户的原文',
                    result_text='Other user translation',
                    finished_at=now,
                    updated_at=now,
                )
                session.add(task)
                await session.flush()

                history = History(
                    user_id=other_user.id,
                    task_id=task.id,
                    title='其他用户的历史',
                    task_type='text',
                    source_lang='zh',
                    target_lang='en',
                    updated_at=now,
                )
                session.add(history)
                await session.commit()
                return history.id, create_access_token(other_user.id)

        other_history_id, other_access_token = asyncio.run(seed_other_user_history())

        forbidden = self.client.get(f'/api/history/{other_history_id}', headers=headers)
        self.assertEqual(forbidden.status_code, 404)

        allowed = self.client.get(
            f'/api/history/{other_history_id}',
            headers={'Authorization': f'Bearer {other_access_token}'},
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertEqual(allowed.json()['data']['id'], other_history_id)

    def test_file_upload_task_lifecycle_and_history_delete(self) -> None:
        headers = self.auth_headers()
        file_hash = 'functionalhash01'
        content = b'fake docx payload'

        check = self.client.post(
            '/api/file/check',
            headers=headers,
            json={
                'file_hash': file_hash,
                'filename': 'sample.docx',
                'file_size': len(content),
                'total_chunks': 1,
            },
        )
        self.assertEqual(check.status_code, 200, check.text)
        self.assertFalse(check.json()['data']['exists'])

        chunk = self.client.post(
            '/api/file/chunk',
            headers=headers,
            data={'file_hash': file_hash, 'chunk_index': '0', 'total_chunks': '1'},
            files={
                'chunk': (
                    'sample.docx',
                    content,
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                )
            },
        )
        self.assertEqual(chunk.status_code, 200, chunk.text)

        merge = self.client.post(
            '/api/file/merge',
            headers=headers,
            json={
                'file_hash': file_hash,
                'filename': 'sample.docx',
                'total_chunks': 1,
                'mime_type': (
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                ),
            },
        )
        self.assertEqual(merge.status_code, 200, merge.text)
        file_id = merge.json()['data']['file_id']

        submit = self.client.post(
            '/api/translate/file',
            headers=headers,
            json={'file_id': file_id, 'source_lang': 'auto', 'target_lang': 'en'},
        )
        self.assertEqual(submit.status_code, 200, submit.text)
        task_payload = submit.json()['data']
        self.assertEqual(task_payload['status'], 'queued')

        status_response = self.client.get(
            f"/api/translate/status/{task_payload['task_id']}",
            headers=headers,
        )
        self.assertEqual(status_response.status_code, 200, status_response.text)
        self.assertEqual(status_response.json()['data']['status'], 'queued')

        blocked = self.client.post(
            '/api/file/check',
            headers=headers,
            json={
                'file_hash': 'functionalhash02',
                'filename': 'other.docx',
                'file_size': len(content),
                'total_chunks': 1,
            },
        )
        self.assertEqual(blocked.status_code, 409)

        cancel = self.client.post(
            f"/api/translate/cancel/{task_payload['task_id']}",
            headers=headers,
        )
        self.assertEqual(cancel.status_code, 200, cancel.text)
        self.assertEqual(cancel.json()['data']['status'], 'cancelled')

        delete = self.client.delete(f"/api/history/{task_payload['history_id']}", headers=headers)
        self.assertEqual(delete.status_code, 204, delete.text)

    def test_file_check_rejects_unsupported_extensions(self) -> None:
        response = self.client.post(
            '/api/file/check',
            headers=self.auth_headers(),
            json={
                'file_hash': 'functionalhash03',
                'filename': 'notes.txt',
                'file_size': 12,
                'total_chunks': 1,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], '仅支持 .docx 和 .pdf')


class ServiceUnitTestCase(unittest.TestCase):
    def test_provider_language_detection_and_document_translation_guard(self) -> None:
        from app.services.provider_service import TranslationProviderError, provider_service

        cases = [
            ('患者每日一次服用。', 'zh'),
            ('Der Patient nimmt das Arzneimittel ein.', 'de'),
            ('Le patient prend la dose prescrite.', 'fr'),
            ('The patient takes one tablet daily.', 'en'),
            ('これはテストです。', 'ja'),
            ('환자는 매일 복용합니다.', 'ko'),
        ]

        for text, expected_lang in cases:
            with self.subTest(expected_lang=expected_lang):
                lang, confidence = asyncio.run(provider_service.detect_language(text))
                self.assertEqual(lang, expected_lang)
                self.assertGreater(confidence, 0)

        fallback = asyncio.run(provider_service.translate('Dose once daily.', 'en', 'zh'))
        self.assertIn('英文 -> 中文', fallback)

        with self.assertRaises(TranslationProviderError):
            asyncio.run(
                provider_service.translate('Dose once daily.', 'en', 'zh', preserve_format=True)
            )

    def test_file_service_validation_and_scanned_pdf_detection(self) -> None:
        from fastapi import HTTPException

        from app.config import settings
        from app.services.file_service import file_service

        file_service._validate_file('sample.docx', 12, 1)
        file_service._validate_file('sample.pdf', 12, 1)

        with self.assertRaises(HTTPException) as unsupported:
            file_service._validate_file('sample.txt', 12, 1)
        self.assertEqual(unsupported.exception.status_code, 400)
        self.assertEqual(unsupported.exception.detail, '仅支持 .docx 和 .pdf')

        with self.assertRaises(HTTPException) as too_large:
            file_service._validate_file(
                'sample.pdf',
                settings.file_max_size_mb * 1024 * 1024 + 1,
                1,
            )
        self.assertEqual(too_large.exception.detail, '文件大小不能超过 100MB')

        with self.assertRaises(HTTPException) as chunk_mismatch:
            file_service._validate_file('sample.pdf', settings.file_chunk_size + 1, 1)
        self.assertEqual(chunk_mismatch.exception.detail, '分片数量与文件大小不匹配')

        with tempfile.TemporaryDirectory() as temp_dir:
            text_pdf = Path(temp_dir) / 'text.pdf'
            text_pdf.write_bytes(b'%PDF-1.7\n/Font\nBT\nET\n')
            self.assertFalse(file_service._is_scanned_pdf(text_pdf))

            scanned_pdf = Path(temp_dir) / 'scanned.pdf'
            scanned_pdf.write_bytes(b'%PDF-1.7\n/Image only stream\n')
            self.assertTrue(file_service._is_scanned_pdf(scanned_pdf))

    def test_document_pdf_keeps_plain_translation_without_paragraph_labels(self) -> None:
        from io import BytesIO

        from pypdf import PdfReader

        from app.services.document_service import MAX_SECTION_CHARS, document_service

        chunks = document_service.split_for_translation('第一段\n第二段')
        self.assertEqual(chunks, ['第一段\n第二段'])

        long_text = 'A' * (MAX_SECTION_CHARS + 20)
        long_chunks = document_service.split_for_translation(f'{long_text}\nB')
        self.assertGreaterEqual(len(long_chunks), 2)

        pdf_bytes = document_service.build_translation_pdf(
            'sample',
            ['Translated paragraph one.', 'Translated paragraph two.'],
        )
        pdf_text = '\n'.join(
            page.extract_text() or '' for page in PdfReader(BytesIO(pdf_bytes)).pages
        )
        self.assertIn('Translated paragraph one.', pdf_text)
        self.assertIn('Translated paragraph two.', pdf_text)
        self.assertNotIn('第 1 段', pdf_text)
        self.assertNotIn('第 2 段', pdf_text)


if __name__ == '__main__':
    unittest.main()
