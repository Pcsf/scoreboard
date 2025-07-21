import unittest
import time
import os
import io
import sys
from scoreboard import Scoreboard, Transaction

class TestTransaction(unittest.TestCase):
    """Tests for the Transaction class."""

    def test_equality(self):
        """Test that two transactions with the same data are equal."""
        t1 = Transaction("data_A", timestamp=1)
        t2 = Transaction("data_A", timestamp=2)
        self.assertEqual(t1, t2, "Transactions with the same data should be equal, regardless of timestamp.")

    def test_inequality(self):
        """Test that two transactions with different data are not equal."""
        t1 = Transaction("data_A")
        t2 = Transaction("data_B")
        self.assertNotEqual(t1, t2, "Transactions with different data should not be equal.")

    def test_inequality_with_other_types(self):
        """Test that a transaction is not equal to an object of a different type."""
        t1 = Transaction("data_A")
        self.assertNotEqual(t1, "data_A", "Transaction should not be equal to a non-Transaction object.")

class TestScoreboard(unittest.TestCase):
    """Tests for the Scoreboard class."""

    def setUp(self):
        """Set up a new scoreboard for each test."""
        test_method = getattr(self, self._testMethodName)
        docstring = test_method.__doc__
        self.scoreboard = Scoreboard(name=f"test_sb_{self.id()}", test_description=docstring)
        self.scoreboard.start()

    def tearDown(self):
        """Stop the scoreboard after each test."""
        self.scoreboard.stop()

    def test_single_match(self):
        """Test a single matching transaction pair."""
        self.scoreboard.write_actual(Transaction("A"))
        self.scoreboard.write_expected(Transaction("A"))
        time.sleep(0.2)  # Allow time for comparison
        self.assertTrue(self.scoreboard.report(), "Report should indicate success for a single match.")
        self.assertEqual(len(self.scoreboard._results), 1)
        self.assertEqual(len(self.scoreboard._mismatches_details), 0)

    def test_single_mismatch(self):
        """Test a single mismatching transaction pair."""
        self.scoreboard.write_actual(Transaction("A"))
        self.scoreboard.write_expected(Transaction("B"))
        time.sleep(0.2)  # Allow time for comparison
        self.assertFalse(self.scoreboard.report(), "Report should indicate failure for a mismatch.")
        self.assertEqual(len(self.scoreboard._results), 1)
        self.assertEqual(len(self.scoreboard._mismatches_details), 1)
        self.assertEqual(self.scoreboard._mismatches_details[0]['line'], 53)

    def test_multiple_transactions(self):
        """Test a mix of matching and mismatching transactions."""
        self.scoreboard.write_actual(Transaction(1))
        self.scoreboard.write_expected(Transaction(1))
        self.scoreboard.write_actual(Transaction(2))
        self.scoreboard.write_expected(Transaction(3)) # Mismatch
        self.scoreboard.write_actual(Transaction(4))
        self.scoreboard.write_expected(Transaction(4))
        time.sleep(0.5)
        self.assertFalse(self.scoreboard.report(), "Report should indicate failure with mixed results.")
        self.assertEqual(len(self.scoreboard._results), 3)
        self.assertEqual(len(self.scoreboard._mismatches_details), 1)
        self.assertEqual(self.scoreboard._mismatches_details[0]['line'], 65)

    def test_no_transactions(self):
        """Test the scoreboard report when no transactions are processed."""
        # Suppress console output for this test
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            self.assertFalse(self.scoreboard.report(), "Report should indicate failure if no comparisons were made.")
        finally:
            sys.stdout = original_stdout

    def test_report_to_file(self):
        """Test that the report is correctly written to a file."""
        report_filename = "test_report.txt"
        if os.path.exists(report_filename):
            os.remove(report_filename)

        self.scoreboard.write_actual(Transaction("file_test"))
        self.scoreboard.write_expected(Transaction("file_test_mismatch"))
        time.sleep(0.2)
        
        self.scoreboard.report(output_file=report_filename)
        
        self.assertTrue(os.path.exists(report_filename))
        with open(report_filename, 'r') as f:
            content = f.read()
            self.assertIn("TEST FAILED", content)
            self.assertIn("Total comparisons: 1", content)
            self.assertIn("Line: 91", content)

        os.remove(report_filename)

    def test_invalid_input(self):
        """Test that writing non-Transaction objects is handled gracefully."""
        # Suppress console output for this test
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            self.scoreboard.write_actual("not a transaction")
            self.scoreboard.write_expected("not a transaction")
            time.sleep(0.2)
            # The queues should be empty as the invalid data is rejected
            self.assertEqual(self.scoreboard._actual_queue.qsize(), 0)
            self.assertEqual(self.scoreboard._expected_queue.qsize(), 0)
            self.assertFalse(self.scoreboard.report()) # No comparisons, so should fail
        finally:
            sys.stdout = original_stdout

if __name__ == '__main__':
    unittest.main()
