#!/usr/bin/env python3
"""
Interactive Real Import Test Script.

This script allows users to test the import functionality using real credentials
and sample data, and then verifies the import by checking the Gmail API.
"""
import os
import sys
import shutil
import tempfile
import subprocess
import mailbox
import time
import email.message

from google.oauth2 import service_account
from googleapiclient import discovery

# Scopes needed for import and verification
SCOPES = [
    'https://www.googleapis.com/auth/gmail.insert',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.readonly'  # Added for verification
]

def get_service(creds_path, user_email):
  """Authenticates and returns the Gmail API service."""
  creds = service_account.Credentials.from_service_account_file(
      creds_path, scopes=SCOPES, subject=user_email
  )
  return discovery.build('gmail', 'v1', credentials=creds)

def count_messages_in_mbox(mbox_path):
  """Counts messages in an mbox file."""
  mbox = mailbox.mbox(mbox_path)
  return len(mbox)

def create_dummy_mbox(filepath):
  """Creates a dummy mbox file with one message if sample.mbox is missing."""
  print("Creating dummy mbox file...")
  mbox = mailbox.mbox(filepath)
  msg = email.message.Message()
  msg['Subject'] = 'Test Message'
  msg['From'] = 'sender@example.com'
  msg['To'] = 'recipient@example.com'
  msg.set_payload('This is a test message body.')
  mbox.add(msg)
  mbox.flush()
  mbox.close()

def verify_import(service, user_email, label_name, expected_count):
  """Verifies that the imported messages exist in Gmail."""
  print(f"\nVerifying import for user: {user_email}")

  # 1. Find the label ID
  results = service.users().labels().list(userId=user_email).execute()
  labels = results.get('labels', [])
  label_id = None
  for label in labels:
    if label['name'].lower() == label_name.lower():
      label_id = label['id']
      break

  if not label_id:
    print(f"Error: Label '{label_name}' not found in Gmail.")
    return False

  print(f"Found label '{label_name}' with ID: {label_id}")

  # 2. List messages with that label
  # Give Gmail a moment to index if needed (though API is usually fast)
  time.sleep(2)

  response = service.users().messages().list(
      userId=user_email, labelIds=[label_id], includeSpamTrash=True
  ).execute()

  messages = response.get('messages', [])
  actual_count = len(messages)

  print(f"Expected messages: {expected_count}")
  print(f"Actual messages found in label: {actual_count}")

  if actual_count == expected_count:
    print("SUCCESS: Import verification passed!")
    return True

  print("FAILURE: Message count mismatch.")
  return False


def main():
  """Main function to run the interactive test."""
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

    dst_mbox_name = "Test Import.mbox"
    dst_mbox_path = os.path.join(user_dir, dst_mbox_name)

    # Copy sample.mbox or create dummy
    src_mbox = "sample.mbox"
    if not os.path.exists(src_mbox):
      # Try to find it if not in current dir
      script_dir = os.path.dirname(os.path.abspath(__file__))
      src_mbox = os.path.join(script_dir, "sample.mbox")

    if os.path.exists(src_mbox):
      print(f"Using existing {src_mbox}")
      shutil.copy(src_mbox, dst_mbox_path)
    else:
      print("sample.mbox not found, generating dummy data.")
      create_dummy_mbox(dst_mbox_path)

    expected_msg_count = count_messages_in_mbox(dst_mbox_path)
    print(f"\nPrepared test data in {temp_dir}")
    print(f"Mbox contains {expected_msg_count} messages.")
    print(f"Importing into {target_email} with label 'Test Import'...")

    # Run import
    cmd = [
        sys.executable,
        "import_mailbox_to_gmail.py",
        "--json", creds_path,
        "--dir", temp_dir
    ]

    subprocess.check_call(cmd)

    print("\nImport script finished. Starting verification...")

    # Verify
    try:
      service = get_service(creds_path, target_email)
      # The label name is derived from the filename "Test Import.mbox" -> "Test Import"
      label_name = "Test Import"
      if verify_import(service, target_email, label_name, expected_msg_count):
        sys.exit(0)
      else:
        sys.exit(1)
    except Exception as e:
      print(f"Verification failed with error: {e}")
      print("Note: Ensure your service account has "
            "'https://www.googleapis.com/auth/gmail.readonly' scope authorized.")
      sys.exit(1)

  except subprocess.CalledProcessError as e:
    print(f"\nImport process failed with exit code {e.returncode}")
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
