"""
Test Suite for NutriRisk AI PWA and Multi-Platform App Mode Capabilities.
Verifies:
  1. /manifest.json returns HTTP 200 with valid JSON and standalone configuration.
  2. /sw.js returns HTTP 200 with Service-Worker-Allowed header.
  3. Static icon assets (192, 512, apple-touch-icon) return HTTP 200.
  4. Template markup contains PWA manifest link and install button elements.
  5. run_desktop_app.py and run_app.bat launcher files are present.
"""
import os
import json
import unittest
from nutririsk import create_app

class TestPWAAndAppMode(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

    def test_01_manifest_json_endpoint(self):
        """Validates that /manifest.json returns valid PWA metadata."""
        resp = self.client.get("/manifest.json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/manifest+json", resp.content_type)
        data = json.loads(resp.get_data(as_text=True))
        
        self.assertEqual(data["name"], "NutriRisk AI — Clinical Decision-Support System")
        self.assertEqual(data["short_name"], "NutriRisk AI")
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["start_url"], "/dashboard")
        self.assertGreaterEqual(len(data["icons"]), 2)

    def test_02_service_worker_endpoint(self):
        """Validates that /sw.js is served with root scope permission header."""
        resp = self.client.get("/sw.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("javascript", resp.content_type)
        self.assertEqual(resp.headers.get("Service-Worker-Allowed"), "/")
        content = resp.get_data(as_text=True)
        self.assertIn("nutririsk-cache", content)
        self.assertIn("addEventListener", content)

    def test_03_pwa_icon_assets_accessible(self):
        """Verifies that all required application icon sizes are accessible via static routes."""
        for icon_path in [
            "/static/img/icon-192.png",
            "/static/img/icon-512.png",
            "/static/img/apple-touch-icon.png"
        ]:
            resp = self.client.get(icon_path)
            self.assertEqual(resp.status_code, 200, f"Icon {icon_path} should be accessible")
            self.assertEqual(resp.content_type, "image/png")

    def test_04_template_includes_pwa_headers_and_install_elements(self):
        """Checks that HTML templates include manifest linkage, mobile meta tags, and install triggers."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        
        self.assertIn('rel="manifest"', html)
        self.assertIn('/manifest.json', html)
        self.assertIn('name="theme-color"', html)
        self.assertIn('name="apple-mobile-web-app-capable"', html)
        self.assertIn('id="publicBtnInstallApp"', html)
        self.assertIn('id="pwaInstallModal"', html)

    def test_05_desktop_app_launchers_exist(self):
        """Verifies that 1-click Windows batch and Python desktop runners exist."""
        self.assertTrue(os.path.exists("run_app.bat"), "run_app.bat must exist")
        self.assertTrue(os.path.exists("run_desktop_app.py"), "run_desktop_app.py must exist")

if __name__ == "__main__":
    unittest.main()
