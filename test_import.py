import unittest
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock, call
import importlib.util
import sys

# Load the module dynamically
spec = importlib.util.spec_from_file_location("import_mailbox_to_gmail", "import-mailbox-to-gmail.py")
import_mailbox_to_gmail = importlib.util.module_from_spec(spec)
sys.modules["import_mailbox_to_gmail"] = import_mailbox_to_gmail
spec.loader.exec_module(import_mailbox_to_gmail)

class TestImport(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.username = 'testuser@example.com'
        self.user_dir = os.path.join(self.test_dir, self.username)
        os.makedirs(self.user_dir)
        self.mbox_path = os.path.join(self.user_dir, 'test.mbox')
        shutil.copyfile('sample.mbox', self.mbox_path)


    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('import_mailbox_to_gmail.discovery.build')
    def test_import(self, mock_build):
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

        import_mailbox_to_gmail.args = args

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

if __name__ == '__main__':
    unittest.main()
