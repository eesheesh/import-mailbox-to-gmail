#!/usr/bin/env python3
import os
import sys
import shutil
import tempfile
import subprocess

def main():
    print("Interactive Real Import Test")
    print("----------------------------")

    # Get credentials path
    if len(sys.argv) > 1:
        creds_path = sys.argv[1]
    else:
        creds_path = input("Enter path to Credentials.json: ").strip()

    if not os.path.exists(creds_path):
        print(f"Error: File '{creds_path}' not found.")
        sys.exit(1)

    # Get target email
    if len(sys.argv) > 2:
        target_email = sys.argv[2]
    else:
        target_email = input("Enter target email address: ").strip()

    if not target_email:
        print("Error: Target email is required.")
        sys.exit(1)

    # Setup temp directory
    temp_dir = tempfile.mkdtemp(prefix="import_test_")
    try:
        user_dir = os.path.join(temp_dir, target_email)
        os.makedirs(user_dir)

        # Copy sample.mbox
        src_mbox = "sample.mbox"
        if not os.path.exists(src_mbox):
             # Try to find it if not in current dir
             script_dir = os.path.dirname(os.path.abspath(__file__))
             src_mbox = os.path.join(script_dir, "sample.mbox")

        if not os.path.exists(src_mbox):
            print("Error: sample.mbox not found.")
            sys.exit(1)

        dst_mbox = os.path.join(user_dir, "Test Import.mbox")
        shutil.copy(src_mbox, dst_mbox)

        print(f"\nPrepared test data in {temp_dir}")
        print(f"Importing into {target_email} with label 'Test Import'...")

        # Run import
        cmd = [
            sys.executable,
            "import_mailbox_to_gmail.py",
            "--json", creds_path,
            "--dir", temp_dir
        ]

        subprocess.check_call(cmd)

        print("\nImport completed successfully.")

    except subprocess.CalledProcessError as e:
        print(f"\nImport failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            print(f"Cleaning up {temp_dir}...")
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
