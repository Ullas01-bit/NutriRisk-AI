"""
Root test runner wrapper.
Run directly using: python test_app.py
"""
import unittest
from tests.test_app import TestAppRoutes
from tests.test_ml import TestMLComponents
from tests.test_db import TestDatabaseImplementation
from tests.test_dashboard import TestUserDashboard
from tests.test_history import TestPredictionHistory
from tests.test_analytics import TestAnalyticsDashboard
from tests.test_admin import TestAdminDashboard
from tests.test_model_info import TestModelInformationPage
from tests.test_pdf_report import TestDownloadablePDFReport
from tests.test_profile import TestProfileManagement
from tests.test_security import TestSecurityAndErrorHandling
from tests.test_qa_master_suite import TestQAMasterSuite
from tests.test_site_audit_e2e import NutriRiskFullWebsiteAudit
from tests.test_final_integration_16steps import TestNutriRiskFinalIntegration16Steps
from tests.test_batch_screening import TestBatchPatientScreening
from tests.test_face_id_and_under18 import TestFaceIdAndUnder18Features
from tests.test_pwa_and_app_mode import TestPWAAndAppMode

if __name__ == "__main__":
    print("=" * 70)
    print("Running NutriRisk AI Test Suite (Integration & Unit Tests)")
    print("=" * 70)
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestAppRoutes))
    suite.addTests(loader.loadTestsFromTestCase(TestMLComponents))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseImplementation))
    suite.addTests(loader.loadTestsFromTestCase(TestUserDashboard))
    suite.addTests(loader.loadTestsFromTestCase(TestPredictionHistory))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyticsDashboard))
    suite.addTests(loader.loadTestsFromTestCase(TestAdminDashboard))
    suite.addTests(loader.loadTestsFromTestCase(TestModelInformationPage))
    suite.addTests(loader.loadTestsFromTestCase(TestDownloadablePDFReport))
    suite.addTests(loader.loadTestsFromTestCase(TestProfileManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityAndErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestQAMasterSuite))
    suite.addTests(loader.loadTestsFromTestCase(NutriRiskFullWebsiteAudit))
    suite.addTests(loader.loadTestsFromTestCase(TestNutriRiskFinalIntegration16Steps))
    suite.addTests(loader.loadTestsFromTestCase(TestBatchPatientScreening))
    suite.addTests(loader.loadTestsFromTestCase(TestFaceIdAndUnder18Features))
    suite.addTests(loader.loadTestsFromTestCase(TestPWAAndAppMode))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        exit(1)
