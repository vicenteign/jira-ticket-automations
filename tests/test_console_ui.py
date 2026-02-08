import io
import unittest
from unittest.mock import patch

from jira_automation.console_ui import ConsoleUI


class TestConsoleUIRequirements(unittest.TestCase):
    def _run_get_requirements(self, inputs):
        ui = ConsoleUI()
        input_iter = iter(inputs)

        def fake_input(prompt=None):
            try:
                return next(input_iter)
            except StopIteration:
                raise EOFError()

        with patch("builtins.input", side_effect=fake_input), patch(
            "sys.stdout", new_callable=io.StringIO
        ):
            return ui.get_requirements()

    def test_allows_single_empty_line_in_content(self):
        result = self._run_get_requirements(["line one", "", "line two", "/done"])
        self.assertEqual(result, "line one\nline two")

    def test_finishes_on_done_command(self):
        result = self._run_get_requirements(["update backend", "/done"])
        self.assertEqual(result, "update backend")

    def test_requires_two_empty_lines_with_no_content(self):
        result = self._run_get_requirements(["", ""])
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
