"""Task-owned development HTTP process; never use this server in production."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
os.chdir(ROOT/"sites")
from frappe.app import serve
serve(port=8005,site="grc.local",no_reload=True,no_threading=False)
