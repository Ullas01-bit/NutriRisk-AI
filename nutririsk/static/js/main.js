/**
 * NutriRisk AI — Clinical Interface Client Script
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Mobile Sidebar Toggle
  const sidebar = document.getElementById("appSidebar");
  const toggleBtn = document.getElementById("mobileSidebarToggle");
  const closeBtn = document.getElementById("closeSidebarBtn");

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("show");
    });
  }

  if (closeBtn && sidebar) {
    closeBtn.addEventListener("click", () => {
      sidebar.classList.remove("show");
    });
  }

  // 2. Real-Time Dynamic BMI Calculator for the Prediction Form
  const heightInput = document.getElementById("inputHeight");
  const weightInput = document.getElementById("inputWeight");
  const bmiBox = document.getElementById("liveBmiBox");
  const bmiValueElem = document.getElementById("liveBmiValue");
  const bmiCatElem = document.getElementById("liveBmiCategory");

  function calculateLiveBMI() {
    if (!heightInput || !weightInput || !bmiBox) return;

    const h = parseFloat(heightInput.value);
    const w = parseFloat(weightInput.value);

    if (h >= 50 && h <= 250 && w >= 15 && w <= 300) {
      const heightM = h / 100.0;
      const bmi = (w / (heightM * heightM)).toFixed(1);
      bmiValueElem.textContent = bmi;

      let category = "Normal weight";
      let catClass = "text-success";

      if (bmi < 18.5) {
        category = "Underweight (Nutritional vulnerability indicator)";
        catClass = "text-danger";
      } else if (bmi < 25.0) {
        category = "Normal baseline weight";
        catClass = "text-success";
      } else if (bmi < 30.0) {
        category = "Overweight";
        catClass = "text-warning";
      } else {
        category = "Obesity range";
        catClass = "text-danger";
      }

      bmiCatElem.textContent = category;
      bmiCatElem.className = `small fw-bold mt-1 ${catClass}`;
      bmiBox.style.display = "flex";
    } else {
      bmiBox.style.display = "none";
    }
  }

  if (heightInput && weightInput) {
    heightInput.addEventListener("input", calculateLiveBMI);
    weightInput.addEventListener("input", calculateLiveBMI);
    // Initial check in case values are pre-filled
    calculateLiveBMI();
  }

  // 3. Form Reset Handler
  const resetBtn = document.getElementById("btnResetAssessment");
  const assessmentForm = document.getElementById("assessmentForm");

  if (resetBtn && assessmentForm) {
    resetBtn.addEventListener("click", (e) => {
      e.preventDefault();
      assessmentForm.reset();
      if (bmiBox) bmiBox.style.display = "none";
    });
  }

  // 4. Form Submission & Loading Overlay
  const loadingOverlay = document.getElementById("loadingOverlay");
  if (assessmentForm && loadingOverlay) {
    assessmentForm.addEventListener("submit", (e) => {
      // Basic check
      if (assessmentForm.checkValidity()) {
        loadingOverlay.style.display = "flex";
      }
    });
  }

  // 5. Auto-dismiss alerts
  const alerts = document.querySelectorAll(".alert-dismissible");
  alerts.forEach((alert) => {
    setTimeout(() => {
      try {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
      } catch (e) {
        // Fallback
        alert.remove();
      }
    }, 5000);
  });

  // 6. Progressive Web App (PWA) Service Worker Registration & App Install Handler
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").then((reg) => {
        console.log("[PWA] Service Worker registered with scope:", reg.scope);
      }).catch((err) => {
        console.warn("[PWA] Service Worker registration failed:", err);
      });
    });
  }

  let deferredPrompt = null;
  const btnInstall = document.getElementById("btnInstallApp");
  const publicBtnInstall = document.getElementById("publicBtnInstallApp");
  const sidebarInstall = document.getElementById("sidebarInstallApp");
  const modalTrigger = document.getElementById("btnModalTriggerInstall");
  const installModalEl = document.getElementById("pwaInstallModal");

  function showInstallButtons() {
    if (btnInstall) btnInstall.classList.remove("d-none");
    if (publicBtnInstall) publicBtnInstall.classList.remove("d-none");
  }

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallButtons();
  });

  async function triggerAppInstall() {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      console.log(`[PWA] Install prompt outcome: ${outcome}`);
      deferredPrompt = null;
      if (btnInstall) btnInstall.classList.add("d-none");
      if (publicBtnInstall) publicBtnInstall.classList.add("d-none");
      if (installModalEl && window.bootstrap) {
        const bsModal = bootstrap.Modal.getInstance(installModalEl);
        if (bsModal) bsModal.hide();
      }
    } else {
      if (installModalEl && window.bootstrap) {
        const modal = new bootstrap.Modal(installModalEl);
        modal.show();
      }
    }
  }

  if (btnInstall) btnInstall.addEventListener("click", triggerAppInstall);
  if (publicBtnInstall) publicBtnInstall.addEventListener("click", triggerAppInstall);
  if (sidebarInstall) sidebarInstall.addEventListener("click", triggerAppInstall);
  if (modalTrigger) modalTrigger.addEventListener("click", triggerAppInstall);

  window.addEventListener("appinstalled", () => {
    console.log("[PWA] NutriRisk AI App installed successfully!");
    if (btnInstall) btnInstall.classList.add("d-none");
    if (publicBtnInstall) publicBtnInstall.classList.add("d-none");
  });
});
