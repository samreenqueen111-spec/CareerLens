"""
CareerLens - Application Entry Point.
Run with:
    python run.py
or
    flask --app run.py run
"""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")

    print("=" * 65)
    print("  [*] Starting CareerLens (Production Suite)")
    print(f"  [+] Local Server: http://{host}:{port}")
    print(f"  [+] Analyzer URL: http://{host}:{port}/analyzer")
    print(f"  [+] Dashboard:    http://{host}:{port}/dashboard")
    print(f"  [+] History:      http://{host}:{port}/history")
    print("=" * 65)

    app.run(host=host, port=port, debug=debug)
