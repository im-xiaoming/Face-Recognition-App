from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase

from face_app.middleware import SERVER_SESSION_KEY, SERVER_SESSION_TOKEN


class TextModeProtectionTests(TestCase):
    def test_text_mode_toggle_visible_but_disabled_for_anonymous_user(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="text-mode-toggle"')
        self.assertContains(response, 'data-can-switch-text="false"')
        self.assertContains(response, 'disabled title=')

    def test_text_mode_toggle_enabled_for_staff_user(self):
        admin = User.objects.create_user(
            username='admin',
            password='admin-password',
            is_staff=True,
        )
        self.client.force_login(admin)
        session = self.client.session
        session[SERVER_SESSION_KEY] = SERVER_SESSION_TOKEN
        session.save()

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="text-mode-toggle"')
        self.assertContains(response, 'data-can-switch-text="true"')
        self.assertNotContains(response, 'disabled title=')

    def test_old_staff_session_is_logged_out_after_server_restart(self):
        admin = User.objects.create_user(
            username='old-admin',
            password='admin-password',
            is_staff=True,
        )
        self.client.force_login(admin)
        session = self.client.session
        session[SERVER_SESSION_KEY] = 'old-server-token'
        session.save()

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-can-switch-text="false"')
        self.assertContains(response, 'disabled title=')

    def test_han_viet_copy_and_normal_copy_are_kept(self):
        response = self.client.get('/')

        required_copy = [
            'Luân Hồi Truy Diện Kính',
            'Cực Đạo Đế Binh',
            'Khai Kính Dò Linh Diện',
            'Linh Ảnh Lưu Chuyển',
            'Ghi Danh',
            'Đạo Môn',
            'Danh Sách Đạo Hữu',
            'data-normal-text="Ứng dụng nhận diện khuôn mặt"',
            'data-normal-text="Nhận diện bằng camera"',
            'data-normal-text="Đăng ký người dùng"',
        ]

        for text in required_copy:
            with self.subTest(text=text):
                self.assertContains(response, text)

    def test_admin_gate_is_preserved_in_template_and_javascript(self):
        base_template = Path('templates/base.html').read_text(encoding='utf-8')
        settings_py = Path('face_app/settings.py').read_text(encoding='utf-8')
        app_js = Path('static/js/app.js').read_text(encoding='utf-8')

        required_guards = [
            'request.user.is_authenticated',
            'request.user.is_staff',
            'data-can-switch-text',
            'disabled title=',
            'LogoutOnServerRestartMiddleware',
            'canSwitchTextMode()',
            'localStorage.removeItem(TEXT_MODE_STORAGE_KEY)',
        ]

        combined = f'{base_template}\n{settings_py}\n{app_js}'
        for guard in required_guards:
            with self.subTest(guard=guard):
                self.assertIn(guard, combined)
