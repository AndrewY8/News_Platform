#!/usr/bin/env python3
"""
Backend deployment preparation script for News Platform on AWS Elastic Beanstalk.
This script prepares the backend deployment package (frontend is deployed separately).
"""

import os
import subprocess
import shutil
import zipfile
from datetime import datetime


def run_command(command, cwd=None):
    """Run a shell command and return the result."""
    print(f"Running: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def create_deployment_package():
    """Create a deployment package for Elastic Beanstalk."""
    print("📦 Creating deployment package...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"news-platform-{timestamp}.zip"

    # Files and directories to exclude
    exclude_patterns = [
        '.git',
        '.github',
        '__pycache__',
        '.pytest_cache',
        'frontend/node_modules',
        'frontend/.next',
        'test_*',
        '*_test_*',
        'debug_*',
        '*.log',
        '.env',
        '.env.*',
        '*.db',
        '*.sqlite*',
        '.vscode',
        '.idea',
        '*.md',
        'README*'
    ]

    def should_exclude(filepath):
        """Check if a file should be excluded from the deployment package."""
        for pattern in exclude_patterns:
            if pattern in filepath or filepath.endswith(pattern.replace('*', '')):
                return True
        return False

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

    print(f"✅ Deployment package created: {zip_filename}")
    print(f"📁 Package size: {os.path.getsize(zip_filename) / 1024 / 1024:.1f} MB")
    return zip_filename


def main():
    """Main deployment preparation process."""
    print("Preparing News Platform Backend for AWS Elastic Beanstalk deployment")
    print("=" * 60)

    # Check if we're in the right directory
    if not os.path.exists("application.py"):
        print("❌ application.py not found. Please run this script from the project root.")
        return False

    # Create deployment package (backend only)
    zip_filename = create_deployment_package()
    if not zip_filename:
        return False

    print("=" * 60)
    print("✅ Backend deployment preparation complete!")
    print(f"📦 Upload '{zip_filename}' to AWS Elastic Beanstalk")
    print()
    print("Next steps:")
    print("1. Go to AWS Elastic Beanstalk console")
    print("2. Create a new Python 3.12 application or update existing one")
    print(f"3. Upload the '{zip_filename}' file")
    print("4. Configure environment variables in EB console:")
    print("   - NEWSAPI_KEY")
    print("   - GEMINI_API_KEY")
    print("   - SUPABASE_URL")
    print("   - SUPABASE_KEY")
    print("   - SECRET_KEY")
    print("   - BACKEND_URL (your EB app URL)")
    print("5. Deploy backend!")
    print()
    print("📝 Note: Frontend (Next.js/React/TypeScript) should be deployed separately")
    print("   to Vercel, Netlify, or another platform that supports dynamic React apps.")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)