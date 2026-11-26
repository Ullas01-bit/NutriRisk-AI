"""
NutriRisk AI Application Entry Point.
Run directly using: python app.py
"""
import os
from nutririsk import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"Starting NutriRisk AI Server at http://127.0.0.1:{port} (debug={debug})")
    app.run(host="127.0.0.1", port=port, debug=debug)
