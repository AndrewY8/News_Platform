#!/usr/bin/env python3
"""Simple deployment ZIP creation for News Platform Backend"""

import os
import zipfile
from datetime import datetime

def create_deployment_zip():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"news-platform-backend-{timestamp}.zip"

    # Files and directories to exclude
    exclude_patterns = [
        '.git', '.github', '__pycache__', '.pytest_cache',
        'frontend', 'test_', '_test_', 'debug_',
        '.log', '.env', '.db', '.sqlite', '.vscode',
        '.idea', '.md', 'README'
    ]

    def should_exclude(filepath):
        for pattern in exclude_patterns:
            if pattern in filepath:
                return True
        return False

    print("Creating backend deployment package...")

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]

            for file in files:
                filepath = os.path.join(root, file)
                if not should_exclude(filepath) and file != zip_filename:
                    arcname = os.path.relpath(filepath, '.')
                    zipf.write(filepath, arcname)
                    print(f"Added: {arcname}")

    size_mb = os.path.getsize(zip_filename) / 1024 / 1024
    print(f"COMPLETE: {zip_filename} ({size_mb:.1f} MB)")
    return zip_filename

if __name__ == "__main__":
    if not os.path.exists("application.py"):
        print("ERROR: Run from project root directory")
        exit(1)

    zip_file = create_deployment_zip()
    print(f"Upload this file to Elastic Beanstalk: {zip_file}")