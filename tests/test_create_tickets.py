import unittest
from unittest.mock import Mock

from jira_automation.main import JiraAutomationApp


class TestCreateTickets(unittest.TestCase):
    def setUp(self):
        self.app = JiraAutomationApp()
        self.app.ui = Mock()
        self.app.jira_client = Mock()

    def test_story_under_epic_uses_epic_link(self):
        tickets = [
            {"index": 0, "type": "Epic", "summary": "Epic A", "description": "", "acceptance_criteria": [], "parent_index": None},
            {"index": 1, "type": "Story", "summary": "Story A", "description": "", "acceptance_criteria": [], "parent_index": 0},
        ]
        self.app.jira_client.create_issue.side_effect = [
            {"key": "KAN-10"},
            {"key": "KAN-11"},
        ]

        created, errors = self.app.create_tickets("KAN", tickets)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(created), 2)
        self.app.jira_client.create_issue.assert_any_call(
            project_key="KAN",
            issue_type="Epic",
            summary="Epic A",
            description="",
            parent_key=None,
            epic_key=None,
        )
        self.app.jira_client.create_issue.assert_any_call(
            project_key="KAN",
            issue_type="Story",
            summary="Story A",
            description="",
            parent_key=None,
            epic_key="KAN-10",
        )

    def test_subtask_skipped_without_parent(self):
        tickets = [
            {"index": 0, "type": "Subtask", "summary": "Subtask A", "description": "", "acceptance_criteria": [], "parent_index": 99},
        ]
        created, errors = self.app.create_tickets("KAN", tickets)

        self.assertEqual(created, [])
        self.assertEqual(errors, ["Skipped subtask (missing parent): Subtask A"])
        self.app.jira_client.create_issue.assert_not_called()

    def test_subtask_under_epic_promoted_to_task(self):
        tickets = [
            {"index": 0, "type": "Epic", "summary": "Epic A", "description": "", "acceptance_criteria": [], "parent_index": None},
            {"index": 1, "type": "Subtask", "summary": "Subtask A", "description": "", "acceptance_criteria": [], "parent_index": 0},
        ]
        self.app.jira_client.create_issue.side_effect = [
            {"key": "KAN-30"},
            {"key": "KAN-31"},
        ]

        created, errors = self.app.create_tickets("KAN", tickets)

        self.assertEqual(len(created), 2)
        self.assertIn("Promoted subtask to Task under Epic: Subtask A", errors)
        self.app.jira_client.create_issue.assert_any_call(
            project_key="KAN",
            issue_type="Task",
            summary="Subtask A",
            description="",
            parent_key=None,
            epic_key="KAN-30",
        )


if __name__ == "__main__":
    unittest.main()
