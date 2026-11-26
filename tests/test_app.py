import os
import unittest
from nutririsk import create_app
from nutririsk.config import Config

class TestConfig(Config):
    TESTING = True
    DATABASE_PATH = "test_nutririsk.db"

class TestAppRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists("test_nutririsk.db"):
            os.remove("test_nutririsk.db")
        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists("test_nutririsk.db"):
            os.remove("test_nutririsk.db")

    def test_01_public_routes(self):
        """Tests that home and model info pages respond with HTTP 200."""
        r_home = self.client.get("/")
        self.assertEqual(r_home.status_code, 200)
        self.assertIn(b"NutriRisk AI", r_home.data)

        r_model = self.client.get("/model")
        self.assertEqual(r_model.status_code, 200)
        self.assertIn(b"Model Architecture", r_model.data)

    def test_02_registration_and_login(self):
        """Tests user registration (first user = admin) and login."""
        # 1. Register Admin
        r_reg = self.client.post("/register", data={
            "name": "Dr. Alex Morgan",
            "email": "admin@nutririsk.org",
            "password": "securepassword123"
        }, follow_redirects=True)
        self.assertEqual(r_reg.status_code, 200)
        self.assertIn(b"Registration successful", r_reg.data)

        # 2. Login
        r_login = self.client.post("/login", data={
            "email": "admin@nutririsk.org",
            "password": "securepassword123"
        }, follow_redirects=True)
        self.assertEqual(r_login.status_code, 200)
        self.assertIn(b"Welcome back", r_login.data)

    def test_03_prediction_workflow(self):
        """Tests assessment submission, stratification, and XAI result display."""
        # Authenticate first
        self.client.post("/login", data={"email": "admin@nutririsk.org", "password": "securepassword123"})

        cases = [
            ("Patient 01 - Frail", {
                "age": 82, "sex": "Female", "height_cm": 150.0, "weight_kg": 36.0,
                "food_groups": 2, "meals_per_day": 1, "activity": "Low",
                "income": "Low", "education": "None", "residence": "Rural", "recent_illness": "Yes"
            }),
            ("Patient 02 - Robust", {
                "age": 28, "sex": "Male", "height_cm": 178.0, "weight_kg": 72.0,
                "food_groups": 7, "meals_per_day": 3, "activity": "High",
                "income": "High", "education": "Higher", "residence": "Urban", "recent_illness": "No"
            })
        ]

        for name, data in cases:
            response = self.client.post("/predict", data={"subject": name, **data}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Nutritional Risk Assessment", response.data)
            self.assertIn(b"Explainable AI", response.data)

        # Test PDF report generation and download
        r_pdf = self.client.get("/result/1/pdf")
        self.assertEqual(r_pdf.status_code, 200)
        self.assertEqual(r_pdf.content_type, "application/pdf")
        self.assertGreater(len(r_pdf.data), 1000)

    def test_04_authenticated_pages(self):
        """Tests access to history, analytics, admin console, and profile."""
        self.client.post("/login", data={"email": "admin@nutririsk.org", "password": "securepassword123"})

        routes = ["/dashboard", "/history", "/analytics", "/admin", "/profile"]
        for route in routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed with {res.status_code}")

    def test_05_unauthorized_access(self):
        """Tests that protected routes reject unauthenticated sessions."""
        anon_client = self.app.test_client()
        res = anon_client.get("/history")
        # Should redirect to login
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

if __name__ == "__main__":
    unittest.main()
