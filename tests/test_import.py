"""Unit tests for import-mailbox-to-gmail."""
import unittest
import os
import shutil
import tempfile
import importlib.util
import sys
from unittest.mock import patch, MagicMock

# Load the module dynamically
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
script_path = os.path.join(parent_dir, "import-mailbox-to-gmail.py")
spec = importlib.util.spec_from_file_location("import_mailbox_to_gmail", script_path)
import_mailbox_to_gmail = importlib.util.module_from_spec(spec)
sys.modules["import_mailbox_to_gmail"] = import_mailbox_to_gmail
spec.loader.exec_module(import_mailbox_to_gmail)

class TestImport(unittest.TestCase):
  """Test case for import logic."""

  def setUp(self):
    self.test_dir = tempfile.mkdtemp()
    self.username = 'testuser@example.com'
    self.user_dir = os.path.join(self.test_dir, self.username)
    os.makedirs(self.user_dir)
    self.mbox_path = os.path.join(self.user_dir, 'test.mbox')
    sample_mbox_path = os.path.join(os.path.dirname(__file__), 'sample.mbox')
    shutil.copyfile(sample_mbox_path, self.mbox_path)


  def tearDown(self):
    shutil.rmtree(self.test_dir)

  @patch('import_mailbox_to_gmail.discovery.build')
  def test_import(self, mock_build):
    """Test the import process."""
    # Mock the service and its methods
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Mock the labels().list() call to return no existing labels
    mock_service.users().labels().list().execute.return_value = {'labels': []}

    # Mock the labels().create() call to return a new label
    mock_service.users().labels().create().execute.return_value = {
        'id': 'LABEL_1',
        'name': 'test'
    }

    # Mock the messages().import_() call
    mock_service.users().messages().import_().execute.return_value = {'id': 'MSG_ID'}

    # Set up the arguments for the script
    args = MagicMock()
    args.dir = self.test_dir
    args.from_message = 0
    args.fix_msgid = True
    args.replace_quoted_printable = True
    args.num_retries = 3
    args.log = 'test.log'
    args.httplib2debuglevel = 0

    import_mailbox_to_gmail.ARGS = args

    # Call the function that processes the mbox files
    result = import_mailbox_to_gmail.process_mbox_files(
        self.username, mock_service, [])

    # Assertions
    self.assertEqual(result[3], 2) # 2 messages imported
    self.assertEqual(result[4], 0) # 0 messages failed

    # Check that the label was created
    self.assertEqual(mock_service.users().labels().create.call_count, 2)
    mock_service.users().labels().create.assert_any_call(
        userId=self.username,
        body={'messageListVisibility': 'show', 'name': 'test', 'labelListVisibility': 'labelShow'}
    )

    # Check that the messages were imported
    self.assertEqual(mock_service.users().messages().import_().execute.call_count, 2)

  @patch('import_mailbox_to_gmail.discovery.build')
  def test_import_label_failure(self, mock_build):
    """Test that failed label creation increments the failure counter."""
    # Mock the service and its methods
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Mock the labels().list() call to return no existing labels
    mock_service.users().labels().list().execute.return_value = {'labels': []}

    # Mock the labels().create() call to raise an exception
    mock_service.users().labels().create().execute.side_effect = Exception("400 Bad Request")

    # Set up the arguments for the script
    args = MagicMock()
    args.dir = self.test_dir
    args.from_message = 0
    args.fix_msgid = True
    args.replace_quoted_printable = True
    args.num_retries = 1
    args.log = 'test.log'
    args.httplib2debuglevel = 0

    import_mailbox_to_gmail.ARGS = args

    # Call the function that processes the mbox files
    result = import_mailbox_to_gmail.process_mbox_files(
        self.username, mock_service, [])

    # Assertions
    # We expect 1 failed label (the one corresponding to test.mbox)
    self.assertEqual(result[2], 1)  # result[2] is number_of_labels_failed

if __name__ == '__main__':
  unittest.main()
