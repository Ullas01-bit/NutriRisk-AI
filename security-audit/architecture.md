# Architecture & Threat Model: NutriRisk AI

## 1. Product Summary & Healthcare Context
NutriRisk AI is an academic clinical decision-support and nutritional triaging web application. It stratifies patients into three risk tiers (**Low Risk**, **Moderate Risk**, **High Risk**) using demographic, anthropometric, and dietary indicators. The application is built with **Flask 3.x**, backed by an **SQLite** database, and executes offline machine learning inference via **scikit-learn** and **XGBoost** pipelines.

## 2. Principals, Authority, and Trust Boundaries
| Principal | Role | Authentication | Permitted Actions |
| :--- | :--- | :--- | :--- |
| **Anonymous** | Public | None | View landing/model transparency page, access login/register/reset endpoints. |
| **Clinician** | `user` | Password (Scrypt) / OTP (6-digit) / Face ID | Run individual patient assessments, batch CSV screening, view personal history, export PDF reports, manage profile. |
| **Administrator** | `admin` | Password / OTP / Face ID + Role Flag | System oversight, user directory management, role promotion/demotion, system telemetry, immutable audit log review. |

### Key Trust Boundaries:
1. **Client-to-Application (HTTP/TLS)**: Untrusted web browser delivering forms, JSON payloads, webcam biometric canvas captures, and CSV uploads.
2. **Application-to-Database (SQLite)**: Parameterized boundaries separating user input from database execution engine.
3. **Application-to-Filesystem (Model Storage)**: Local path boundaries preventing path traversal or untrusted pickle/joblib deserialization.
4. **Tenant Isolation**: Strict `user_id` separation ensuring clinicians can only inspect, search, and download their own patient records.

## 3. Tech Stack & Deployment Surface
- **Runtime**: Python 3.12, Flask, Jinja2.
- **Data Layer**: SQLite (`nutririsk.db`) with foreign key enforcement and automated migration routines.
- **ML Engine**: Scikit-Learn Pipeline (`ColumnTransformer`, `StandardScaler`, `OneHotEncoder`) with `XGBClassifier` and TreeSHAP occlusion explainability.
- **Client**: Bootstrap 5, Chart.js, HTML5 Canvas (Biometric video stream capture).

## 4. Entry Surfaces & Sinks
- **Auth Routes** (`/login`, `/register`, `/auth/face-login`, `/send-otp`, `/verify-otp`, `/otp-login`, `/reset`): Process user credentials, biometric frames, and one-time codes. Sinks: SQLite `users` and `otp_verifications` tables, Flask secure session.
- **Assessment Submission** (`/predict`, `/batch`): Ingests patient clinical metrics (age, height, weight, dietary diversity). Sinks: Feature engineering (BMI computation), Scikit-Learn `pipeline.predict_proba()`, SQLite `assessments` table.
- **History & PDF Export** (`/history`, `/result/<aid>/pdf`): Searches and renders clinical evaluations. Sinks: SQLite queries, ReportLab / PDF canvas generation.
- **Admin Management** (`/admin`, `/admin/user/<uid>/role`, `/admin/user/<uid>/delete`): Modifies roles and deletes accounts. Sinks: SQLite role updates, cascade deletions, and `admin_audit_logs`.
