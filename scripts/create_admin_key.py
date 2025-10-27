"""Create an admin API key and print the plaintext token once.

Usage (PowerShell):
    $env:METADATA_DIR = "C:\path\to\metadata"  # optional, defaults to ./metadata
    .\.venv\Scripts\python.exe .\scripts\create_admin_key.py

Outputs the token to stdout. Save it now; it will not be stored in plaintext.
"""
import os
import sys

# Ensure we can import storage from project
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from storage import add_api_key_entry

if __name__ == "__main__":
    token = add_api_key_entry("admin")
    print("ADMIN_TOKEN:", token)
