import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from actions.coding_workflow import run_coding_workflow

class TestCodingWorkflow(unittest.TestCase):

    def setUp(self):
        self.player = MagicMock()

    @patch("actions.coding_workflow.is_git_repository")
    @patch("actions.coding_workflow.run_ip_army")
    @patch("subprocess.run")
    @patch("actions.coding_workflow.git_assistant")
    def test_workflow_happy_path(self, mock_git, mock_sub_run, mock_ip_army, mock_is_git):
        # Setup mocks
        mock_is_git.return_value = False
        mock_ip_army.return_value = "Code modifications completed by IP Army."
        
        # Test success: subprocess returns exit code 0
        mock_test_proc = MagicMock()
        mock_test_proc.returncode = 0
        mock_test_proc.stdout = "All tests passed"
        mock_test_proc.stderr = ""
        mock_sub_run.return_value = mock_test_proc
        
        mock_git.return_value = "Staged and committed changes successfully."

        params = {
            "project_path": "dummy_path",
            "instruction": "create a file manager",
            "test_command": "pytest",
            "auto_commit": True
        }

        res = run_coding_workflow(params, player=self.player)
        self.assertIn("Elite Coding Workflow Succeeded", res)
        mock_ip_army.assert_called_once_with("dummy_path", "create a file manager", player=self.player)
        mock_sub_run.assert_called_once()
        mock_git.assert_called_once_with(action_type="commit", project_path="dummy_path", player=self.player)

    @patch("actions.coding_workflow.is_git_repository")
    @patch("actions.coding_workflow.run_ip_army")
    @patch("subprocess.run")
    @patch("actions.coding_workflow.diagnose_and_heal_command")
    @patch("actions.coding_workflow.git_assistant")
    def test_workflow_self_healing(self, mock_git, mock_heal, mock_sub_run, mock_ip_army, mock_is_git):
        mock_is_git.return_value = False
        mock_ip_army.return_value = "Code modifications completed."
        
        # First test run fails (exit code 1), second test run succeeds (exit code 0) after healing
        mock_fail_proc = MagicMock()
        mock_fail_proc.returncode = 1
        mock_fail_proc.stdout = "Test failed with AssertionError"
        mock_fail_proc.stderr = ""
        
        mock_success_proc = MagicMock()
        mock_success_proc.returncode = 0
        mock_success_proc.stdout = "All tests passed after healing"
        mock_success_proc.stderr = ""
        
        mock_sub_run.side_effect = [mock_fail_proc, mock_success_proc]
        mock_heal.return_value = "Successfully diagnosed and healed test failures."
        mock_git.return_value = "Committed changes."

        params = {
            "project_path": "dummy_path",
            "instruction": "fix connection bug",
            "test_command": "pytest",
            "auto_commit": True
        }

        res = run_coding_workflow(params, player=self.player)
        self.assertIn("Elite Coding Workflow Succeeded", res)
        mock_heal.assert_called_once_with("pytest", cwd="dummy_path", max_rounds=3, ui=self.player)
        self.assertEqual(mock_sub_run.call_count, 2)
        mock_git.assert_called_once()

    @patch("actions.coding_workflow.is_git_repository")
    @patch("actions.coding_workflow.create_stash_backup")
    @patch("actions.coding_workflow.rollback_git_changes")
    @patch("actions.coding_workflow.run_ip_army")
    @patch("subprocess.run")
    @patch("actions.coding_workflow.diagnose_and_heal_command")
    def test_workflow_failure_rollback(self, mock_heal, mock_sub_run, mock_ip_army, mock_rollback, mock_stash, mock_is_git):
        mock_is_git.return_value = True
        mock_stash.return_value = False  # clean repo, not stashed
        
        mock_ip_army.return_value = "Modified code."
        
        mock_fail_proc = MagicMock()
        mock_fail_proc.returncode = 1
        mock_fail_proc.stdout = "Fail"
        mock_fail_proc.stderr = ""
        mock_sub_run.return_value = mock_fail_proc
        
        mock_heal.return_value = "Could not heal."
        
        params = {
            "project_path": "dummy_path",
            "instruction": "break something",
            "test_command": "pytest",
            "auto_commit": True
        }
        
        res = run_coding_workflow(params, player=self.player)
        self.assertIn("Workspace Rolled Back", res)
        mock_rollback.assert_called_once()
        args, kwargs = mock_rollback.call_args
        self.assertEqual(args[0], "dummy_path")
        self.assertFalse(args[2])  # stashed is False

    @patch("actions.coding_workflow.is_git_repository")
    @patch("actions.coding_workflow.create_stash_backup")
    @patch("actions.coding_workflow.rollback_git_changes")
    @patch("actions.coding_workflow.run_ip_army")
    @patch("subprocess.run")
    @patch("actions.coding_workflow.diagnose_and_heal_command")
    def test_workflow_failure_rollback_dirty(self, mock_heal, mock_sub_run, mock_ip_army, mock_rollback, mock_stash, mock_is_git):
        mock_is_git.return_value = True
        mock_stash.return_value = True  # dirty repo, stashed
        
        mock_ip_army.return_value = "Modified code."
        
        mock_fail_proc = MagicMock()
        mock_fail_proc.returncode = 1
        mock_fail_proc.stdout = "Fail"
        mock_fail_proc.stderr = ""
        mock_sub_run.return_value = mock_fail_proc
        
        mock_heal.return_value = "Could not heal."
        
        params = {
            "project_path": "dummy_path",
            "instruction": "break something else",
            "test_command": "pytest",
            "auto_commit": True
        }
        
        res = run_coding_workflow(params, player=self.player)
        self.assertIn("Workspace Rolled Back", res)
        mock_rollback.assert_called_once()
        args, kwargs = mock_rollback.call_args
        self.assertEqual(args[0], "dummy_path")
        self.assertTrue(args[2])  # stashed is True

    @patch("actions.coding_workflow.run_git_cmd")
    def test_git_helpers(self, mock_run_git):
        from actions.coding_workflow import is_git_repository, get_git_status, find_stash_index
        
        # Test is_git_repository True
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "true\n"
        mock_run_git.return_value = mock_res
        self.assertTrue(is_git_repository("dummy_path"))
        mock_run_git.assert_called_with(["rev-parse", "--is-inside-work-tree"], "dummy_path")
        
        # Test get_git_status
        mock_res.stdout = " M file.py\n"
        self.assertEqual(get_git_status("dummy_path"), "M file.py")
        
        # Test find_stash_index
        mock_res.returncode = 0
        mock_res.stdout = "stash@{0}: On master: ip_prime_backup_12345\nstash@{1}: On master: other_stash\n"
        self.assertEqual(find_stash_index("dummy_path", "ip_prime_backup_12345"), "stash@{0}")

if __name__ == "__main__":
    unittest.main()
