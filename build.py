import unittest
import subprocess
import sys

def run_tests():
    """Runs the unit tests."""
    loader = unittest.TestLoader()
    suite = loader.discover('.')
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    return len(result.failures) == 0 and len(result.errors) == 0

def create_executable():
    """Creates the executable using PyInstaller."""
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found, installing...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        except subprocess.CalledProcessError as e:
            print(f"Failed to install PyInstaller: {e}")
            sys.exit(1)

    print("Running PyInstaller...")
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--onefile', 'import_mailbox_to_gmail.py'])

if __name__ == '__main__':
    if run_tests():
        print("Tests passed, creating executable...")
        create_executable()
    else:
        print("Tests failed, not creating executable.")
        sys.exit(1)
