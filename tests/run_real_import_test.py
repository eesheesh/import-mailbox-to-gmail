#!/usr/bin/env python3
"""
Interactive Real Import Test Script.

This script allows users to test the import functionality using real credentials
and generated test data, and then verifies the import by checking the Gmail API.
"""
import os
import sys
import shutil
import tempfile
import subprocess
import mailbox
import time
import email.message
import uuid
import random
import logging

from google.oauth2 import service_account
from googleapiclient import discovery
from googleapiclient.errors import HttpError

# Scopes needed for import and verification
SCOPES = [
    'https://www.googleapis.com/auth/gmail.insert',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.readonly'  # Added for verification
]

# Configure logging for the test script
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_service(creds_path, user_email):
  """Authenticates and returns the Gmail API service."""
  creds = service_account.Credentials.from_service_account_file(
      creds_path, scopes=SCOPES, subject=user_email
  )
  return discovery.build('gmail', 'v1', credentials=creds)

def execute_with_retry(request, num_retries=5):
  """Executes an API request with exponential backoff retries."""
  for n in range(num_retries):
    try:
      return request.execute()
    except (HttpError, OSError) as e:
      if n == num_retries - 1:
        raise
      sleep_time = (2 ** n) + random.random()
      logging.warning(
          "Request failed with %s, retrying in %.2f seconds...", e, sleep_time
      )
      time.sleep(sleep_time)
  return None

def create_dummy_mbox(filepath, message_id, date_string):
  """Creates a dummy mbox file with one message having specific headers."""
  print(f"Creating dummy mbox file at {filepath}...")
  mbox = mailbox.mbox(filepath)
  msg = email.message.Message()
  msg['Subject'] = 'Test Import Message'
  msg['From'] = 'sender@example.com'
  msg['To'] = 'recipient@example.com'
  msg['Date'] = date_string
  msg['Message-ID'] = message_id
  msg.set_payload('This is a test message body for verifying import functionality.')
  mbox.add(msg)
  mbox.flush()
  mbox.close()

def get_label_id(service, user_email, label_name):
  """Finds the label ID for a given label name, handling pagination."""
  page_token = None
  while True:
    response = execute_with_retry(
        service.users().labels().list(
            userId=user_email, pageToken=page_token
        )
    )
    labels = response.get('labels', [])
    for label in labels:
      if label['name'].lower() == label_name.lower():
        return label['id']
    page_token = response.get('nextPageToken')
    if not page_token:
      break
  return None

def verify_import(service, user_email, label_name, message_id, expected_date, expected_subject): # pylint: disable=too-many-arguments,too-many-positional-arguments
  """Verifies that the imported message exists in Gmail with correct attributes."""
  print(f"\nVerifying import for user: {user_email}")

  # 1. Find the label ID
  label_id = get_label_id(service, user_email, label_name)

  if not label_id:
    print(f"Error: Label '{label_name}' not found in Gmail.")
    return False

  print(f"Found label '{label_name}' with ID: {label_id}")

  # 2. Search for the message by Message-ID
  query = f"rfc822msgid:{message_id}"
  print(f"Searching for message with query: {query}")

  response = execute_with_retry(
      service.users().messages().list(
          userId=user_email, q=query, includeSpamTrash=True
      )
  )

  messages = response.get('messages', [])

  if not messages:
    print("FAILURE: Message not found by Message-ID.")
    return False

  # Get full message details
  msg_id = messages[0]['id']
  print(f"Found message with Gmail ID: {msg_id}")

  msg_detail = execute_with_retry(
      service.users().messages().get(userId=user_email, id=msg_id)
  )

  # Check Label
  if label_id not in msg_detail.get('labelIds', []):
    print(f"FAILURE: Message does not have the expected label ID {label_id}.")
    print(f"Actual labels: {msg_detail.get('labelIds')}")
    return False

  # Check Headers (Subject, Date)
  headers = msg_detail.get('payload', {}).get('headers', [])
  subject = next((h['value'] for h in headers if h['name'] == 'Subject'), None)
  date = next((h['value'] for h in headers if h['name'] == 'Date'), None)

  if subject != expected_subject:
    print(f"FAILURE: Subject mismatch. Expected: '{expected_subject}', Found: '{subject}'")
    return False

  if date != expected_date:
    print(f"FAILURE: Date mismatch. Expected: '{expected_date}', Found: '{date}'")
    return False

  print("SUCCESS: Import verification passed! Message found with correct Label, Subject, and Date.")
  return True


def get_user_inputs():
  """Gets credentials path and target email from args or input."""
  if len(sys.argv) > 1:
    creds_path = sys.argv[1]
  else:
    creds_path = input("Enter path to Credentials.json: ").strip()

  if not os.path.exists(creds_path):
    print(f"Error: File '{creds_path}' not found.")
    sys.exit(1)

  if len(sys.argv) > 2:
    target_email = sys.argv[2]
  else:
    target_email = input("Enter target email address: ").strip()

  if not target_email:
    print("Error: Target email is required.")
    sys.exit(1)

  return creds_path, target_email


def generate_test_data(user_dir):
  """Generates test mbox data."""
  dst_mbox_name = "Test Import.mbox"
  dst_mbox_path = os.path.join(user_dir, dst_mbox_name)

  # Generate test data
  message_id = f"<{uuid.uuid4()}@test.local>"
  date_string = "Mon, 20 Jan 2025 12:00:00 -0000"

  # Always create a fresh dummy mbox to ensure controlled test data
  create_dummy_mbox(dst_mbox_path, message_id, date_string)

  # Append invalid message to Test Import.mbox
  print(f"Appending invalid message to {dst_mbox_path}...")
  mbox = mailbox.mbox(dst_mbox_path)
  msg = email.message.Message()
  msg['Subject'] = 'Invalid Headers Message'
  msg['Date'] = date_string
  msg['Message-ID'] = f"<{uuid.uuid4()}@test.local>"
  msg['To'] = 'recipient@example.com'
  # Add duplicate From headers
  msg.add_header('From', 'sender1@example.com')
  msg.add_header('From', 'sender2@example.com')
  msg.set_payload('This message has two From headers.')
  mbox.add(msg)
  mbox.flush()
  mbox.close()

  # Create Outbox.mbox (invalid label)
  outbox_path = os.path.join(user_dir, "Outbox.mbox")
  create_dummy_mbox(outbox_path, f"<{uuid.uuid4()}@test.local>", date_string)

  return message_id, date_string


def main():
  """Main function to run the interactive test."""
  print("Interactive Real Import Test")
  print("----------------------------")

  creds_path, target_email = get_user_inputs()

  # Setup temp directory
  temp_dir = tempfile.mkdtemp(prefix="import_test_")
  try:
    user_dir = os.path.join(temp_dir, target_email)
    os.makedirs(user_dir)

    message_id, date_string = generate_test_data(user_dir)
    subject_string = "Test Import Message"

    print(f"\nPrepared test data in {temp_dir}")
    print(f"Message-ID: {message_id}")
    print(f"Importing into {target_email} with label 'Test Import'...")

    # Log file
    log_file = os.path.join(temp_dir, 'import.log')

    # Run import
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(parent_dir, "import-mailbox-to-gmail.py")
    cmd = [
        sys.executable,
        script_path,
        "--json", creds_path,
        "--dir", temp_dir,
        "--log", log_file
    ]

    subprocess.check_call(cmd)

    print("\nImport script finished. Verifying logs and result...")

    # Read log file
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    # Check for skipped Outbox label
    # "Skipping label 'Outbox' because it can't be created"
    if "Skipping label 'Outbox' because it can't be created" not in log_content:
        print("FAILURE: Log does not indicate that 'Outbox' label was skipped.")
        sys.exit(1)
    else:
        print("SUCCESS: Log indicates 'Outbox' label was skipped.")

    # Check for failed message
    # "Failed to import mbox message"
    if "Failed to import mbox message" not in log_content:
        print("FAILURE: Log does not indicate message failure (expected due to invalid headers).")
        sys.exit(1)
    else:
        print("SUCCESS: Log indicates message failure.")

    # Verify successful import
    try:
      service = get_service(creds_path, target_email)
      # The label name is derived from the filename "Test Import.mbox" -> "Test Import"
      label_name = "Test Import"
      if verify_import(service, target_email, label_name, message_id, date_string, subject_string):
        sys.exit(0)
      else:
        sys.exit(1)
    except Exception as e: # pylint: disable=broad-exception-caught
      print(f"Verification failed with error: {e}")
      print("Note: Ensure your service account has "
            "'https://www.googleapis.com/auth/gmail.readonly' scope authorized.")
      sys.exit(1)

  except subprocess.CalledProcessError as e:
    print(f"\nImport process failed with exit code {e.returncode}")
    sys.exit(e.returncode)
  except Exception as e: # pylint: disable=broad-exception-caught
    print(f"\nAn error occurred: {e}")
    sys.exit(1)
  finally:
    # Cleanup
    if os.path.exists(temp_dir):
      print(f"Cleaning up {temp_dir}...")
      shutil.rmtree(temp_dir)

if __name__ == "__main__":
  main()
