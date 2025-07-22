import inspect
import queue
import threading
import time
import sys # Import sys to write to stdout and stderr

# Define a simple Transaction class for demonstration purposes
# In a real testbench, this would represent the data being monitored
class Transaction:
    """Represents a single data transaction or event.

    This class is designed to be flexible and can be used as-is for simple data
    types or extended for more complex scenarios.

    Attributes:
        data: The data content of the transaction. This can be any data structure
              that supports equality comparison (e.g., primitives, dicts, lists,
              or custom objects).
        timestamp (float): The time when the transaction occurred, in seconds
                           since the epoch. Defaults to the time of creation.
        line (int, optional): The line number in the source code where the
                              transaction was created. This is captured automatically
                              and is useful for debugging.

    Usage Examples:
        # For simple data
        simple_txn = Transaction("some_string_data")
        dict_txn = Transaction({"key": "value", "id": 123})

        # For complex data, you can extend the class
        class CustomTransaction(Transaction):
            def __eq__(self, other):
                # Implement custom comparison logic
                if not isinstance(other, CustomTransaction):
                    return False
                # Example: Compare only a specific key in the data dictionary
                return self.data.get("id") == other.data.get("id")

        custom_txn_1 = CustomTransaction({"id": 1, "payload": "data1"})
        custom_txn_2 = CustomTransaction({"id": 1, "payload": "data2"})
        # custom_txn_1 == custom_txn_2 will be True due to the custom __eq__
    """
    def __init__(self, data, timestamp=None):
        self.data = data
        self.timestamp = timestamp if timestamp is not None else time.time()
        try:
            # Get the frame of the caller to capture the line number
            caller_frame = inspect.currentframe().f_back
            self.line = caller_frame.f_lineno
        except Exception:
            self.line = None

    def __eq__(self, other):
        """Check if two Transaction instances are equal based on their data.

        This default implementation performs a deep comparison of the `data`
        attribute. For complex objects, you may want to override this method
        in a subclass to provide custom comparison logic.

        Args:
            other: The other Transaction instance to compare with.

        Returns:
            bool: True if the data attributes are equal, False otherwise.
        """
        if not isinstance(other, Transaction):
            return NotImplemented
        # The default comparison is a deep equality check on the data.
        # This works well for primitives, dicts, and lists.
        return self.data == other.data

    def __repr__(self):
        """Generate a string representation for debugging and reporting.

        Returns:
            str: A formatted string with transaction details.
        """
        return f"Transaction(data={self.data}, timestamp={self.timestamp:.4f}, line={self.line})"

class Scoreboard:
    """
    A simple scoreboard class for comparing actual vs. expected data streams.

    Inspired by verification scoreboard concepts. It uses queues to handle
    asynchronous data arrival and performs comparisons.

    Attributes:
        name: The name of the scoreboard instance.
        test_description: A description of the test case.
        _actual_queue: Queue for actual data received from the test environment.
        _expected_queue: Queue for expected data provided by a reference model.
        _comparison_lock: Lock for thread-safe access to comparison results.
        _results: List to store comparison results (True for match, False for mismatch).
        _mismatches_details: List to store details of mismatches.
        _running: Flag to indicate if the scoreboard is actively comparing.
        _comparison_thread: Thread for performing comparison in the background.
        _stop_event: Event to signal the comparison thread to stop.
    """

    def __init__(self, name="scoreboard", test_description=None):
        """
        Initializes the scoreboard.

        Args:
            name (str): The name of the scoreboard instance.
            test_description (str, optional): A description of the test case.
        """
        self.name = name
        self.test_description = test_description
        # Queue for actual data received from the test environment
        self._actual_queue = queue.Queue()
        # Queue for expected data provided by a reference model or generator
        self._expected_queue = queue.Queue()
        # Lock for thread-safe access to comparison results and mismatches
        self._comparison_lock = threading.Lock()
        # List to store comparison results (True for match, False for mismatch)
        self._results = []
        # List to store details of mismatches (actual, expected)
        self._mismatches_details = []
        # List to store all log messages
        self._log_messages = []
        # Flag to indicate if the scoreboard is actively comparing
        self._running = False
        # Thread for performing comparison in the background
        self._comparison_thread = None
        # Event to signal the comparison thread to stop
        self._stop_event = threading.Event()

        self._log(f"Scoreboard initialized.")

    def _log(self, message):
        """Logs a message to the console and stores it for reporting."""
        full_message = f"[{self.name}] {message}"
        print(full_message)
        self._log_messages.append(full_message)

    def write_actual(self, transaction: Transaction):
        """
        Receives an actual transaction from the test environment.

        Args:
            transaction (Transaction): The actual transaction object.

        Raises:
            ValueError: If the transaction is not an instance of Transaction.
        """
        if not isinstance(transaction, Transaction):
            self._log(f"Warning: Received non-Transaction object for actual data.")
            return
        self._actual_queue.put(transaction)
        self._log(f"Received actual: {transaction}")

    def write_expected(self, transaction: Transaction):
        """
        Receives an expected transaction from a reference model.

        Args:
            transaction (Transaction): The expected transaction object.

        Raises:
            ValueError: If the transaction is not an instance of Transaction.
        """
        if not isinstance(transaction, Transaction):
            self._log(f"Warning: Received non-Transaction object for expected data.")
            return
        self._expected_queue.put(transaction)
        self._log(f"Received expected: {transaction}")

    def _compare_transactions(self):
        """
        Internal method to continuously compare transactions from the queues.
        Runs in a separate thread.
        """
        self._log(f"Comparison thread started.")
        while not self._stop_event.is_set() or not (self._actual_queue.empty() and self._expected_queue.empty()):
            actual_txn = None
            expected_txn = None

            try:
                # Attempt to get transactions with a timeout
                actual_txn = self._actual_queue.get(timeout=0.1)
                expected_txn = self._expected_queue.get(timeout=0.1)

                match = (actual_txn == expected_txn)

                with self._comparison_lock:
                    self._results.append(match)
                    if not match:
                        # Store mismatch details
                        self._mismatches_details.append({
                            "actual": actual_txn,
                            "expected": expected_txn,
                            "line": actual_txn.line
                        })


                if match:
                    self._log(f"MATCH: Actual={actual_txn}, Expected={expected_txn}")
                else:
                    self._log(f"MISMATCH: Actual={actual_txn}, Expected={expected_txn}")

            except queue.Empty:
                # If one queue is empty, wait a bit before checking again
                # This handles cases where data arrives asynchronously
                time.sleep(0.01)
            except Exception as e:
                self._log(f"Error during comparison: {e}")
                # In case of error, mark as mismatch for safety
                with self._comparison_lock:
                     self._results.append(False)
                     # Store error details as a mismatch
                     self._mismatches_details.append({
                         "error": str(e),
                         "actual": actual_txn, # May be None
                         "expected": expected_txn # May be None
                     })


        self._log(f"Comparison thread stopped.")


    def start(self):
        """
        Starts the background comparison thread.

        Raises:
            RuntimeError: If the scoreboard is already running.
        """
        if not self._running:
            self._running = True
            self._stop_event.clear()
            self._comparison_thread = threading.Thread(target=self._compare_transactions)
            self._comparison_thread.start()
            self._log(f"Scoreboard started.")
        else:
            self._log(f"Scoreboard is already running.")

    def stop(self):
        """
        Stops the background comparison thread and waits for it to finish.

        Raises:
            RuntimeError: If the scoreboard is not running.
        """
        if self._running:
            self._log(f"Stopping scoreboard...")
            self._stop_event.set() # Signal thread to stop
            if self._comparison_thread and self._comparison_thread.is_alive():
                 self._comparison_thread.join(timeout=5) # Wait for thread to finish
                 if self._comparison_thread.is_alive():
                     self._log(f"Warning: Comparison thread did not stop gracefully.")
            self._running = False
            self._log(f"Scoreboard stopped.")
        else:
            self._log(f"Scoreboard is not running.")


    def report(self, output_file=None, format='text'):
        """
        Generates a report based on the comparison results and optionally writes it to a file.
        Includes details for any mismatches found.

        Args:
            output_file (str, optional): The path to a file where the report should be saved.
                                     If None, the report is only printed to the console.
            format (str): The format of the report ('text' or 'html').
                          If 'html', the output_file should have an .html extension.

        Returns:
            bool: True if all comparisons were successful, False otherwise.

        Raises:
            IOError: If there's an error writing to the output file.
        """
        if format == 'html':
            if not output_file or not output_file.endswith('.html'):
                self._log(f"Error: HTML format requires an output file ending with .html.")
                return False
            report_content = self._generate_html_report()
            try:
                with open(output_file, 'w') as f:
                    f.write(report_content)
                self._log(f"HTML report saved to {output_file}")
            except IOError as e:
                self._log(f"Error writing HTML report to {output_file}: {e}")
                return False
            return len(self._mismatches_details) == 0 and len(self._results) > 0

        # Text-based reporting
        f = None
        try:
            if output_file:
                f = open(output_file, 'w')
            else:
                f = sys.stdout

            def write_line(line):
                """Helper function to write to the specified output."""
                print(line, file=f)
                if f != sys.stdout:
                    print(line) # Also print to console if writing to a file

            write_line(f"\n[{self.name}] --- Scoreboard Report ---")
            if self.test_description:
                write_line(f"Test Description: {self.test_description}")
            total_comparisons = len(self._results)
            mismatches = len(self._mismatches_details)
            matches = total_comparisons - mismatches

            write_line(f"Total comparisons: {total_comparisons}")
            write_line(f"Matches: {matches}")
            write_line(f"Mismatches: {mismatches}")

            success = (mismatches == 0 and total_comparisons > 0)

            if mismatches > 0:
                write_line("\n--- Mismatch Details ---")
                for i, mismatch in enumerate(self._mismatches_details):
                    write_line(f"Mismatch {i+1}:")
                    if "error" in mismatch:
                        write_line(f"  Error: {mismatch['error']}")
                    write_line(f"  Actual: {mismatch.get('actual', 'N/A')}")
                    write_line(f"  Expected: {mismatch.get('expected', 'N/A')}")
                    if mismatch.get('line') is not None:
                        write_line(f"  Line: {mismatch.get('line')}")
                write_line("------------------------")

            if success:
                write_line(f"[{self.name}] TEST PASSED: No mismatches found.")
            elif total_comparisons == 0:
                write_line(f"[{self.name}] WARNING: No comparisons were performed.")
                success = False
            else:
                write_line(f"[{self.name}] TEST FAILED: Mismatches detected.")

            write_line(f"[{self.name}] ---------------------------\n")

            return success

        except IOError as e:
            self._log(f"Error writing report: {e}")
            return False
        finally:
            if f and f != sys.stdout:
                f.close()

    def _generate_html_report(self):
        """Generates an HTML report of the scoreboard results."""
        total_comparisons = len(self._results)
        mismatches_count = len(self._mismatches_details)
        matches_count = total_comparisons - mismatches_count
        
        if total_comparisons == 0:
            success = False
            status = "WARNING"
            status_color = "orange"
        else:
            success = (mismatches_count == 0)
            status = "PASSED" if success else "FAILED"
            status_color = "green" if success else "red"

        # HTML Body
        body = f"""
        <h1>Scoreboard Report: {self.name}</h1>
        <h2>Test Description: {self.test_description or 'N/A'}</h2>
        <hr>
        <h2>Summary</h2>
        <p><strong>Total comparisons:</strong> {total_comparisons}</p>
        <p><strong>Matches:</strong> {matches_count}</p>
        <p><strong>Mismatches:</strong> {mismatches_count}</p>
        <h2 style="color:{status_color};">Overall Status: {status}</h2>
        """

        if total_comparisons == 0:
            body += "<p><strong>Warning:</strong> No comparisons were performed.</p>"

        if mismatches_count > 0:
            body += "<h2>Mismatch Details</h2>"
            body += "<table border='1'><tr><th>#</th><th>Details</th></tr>"
            for i, mismatch in enumerate(self._mismatches_details):
                details = ""
                if "error" in mismatch:
                    details += f"<strong>Error:</strong> {mismatch['error']}<br>"
                details += f"<strong>Actual:</strong> {mismatch.get('actual', 'N/A')}<br>"
                details += f"<strong>Expected:</strong> {mismatch.get('expected', 'N/A')}<br>"
                if mismatch.get('line') is not None:
                    details += f"<strong>Line:</strong> {mismatch.get('line')}"
                body += f"<tr><td>{i+1}</td><td>{details}</td></tr>"
            body += "</table>"

        body += "<h2>Execution Log</h2>"
        body += f"<pre><code>"
        for msg in self._log_messages:
            body += msg + "\n"
        body += "</code></pre>"

        # Full HTML Document
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Scoreboard Report: {self.name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1, h2 {{ color: #333; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; vertical-align: top; }}
                tr:hover {{ background-color: #f5f5f5; }}
                pre {{ background-color: #f4f4f4; padding: 10px; border: 1px solid #ddd; white-space: pre-wrap; }}
            </style>
        </head>
        <body>
            {body}
        </body>
        </html>
        """
        return html_template

# Example Usage:
if __name__ == "__main__":
    # Create a scoreboard instance
    my_scoreboard = Scoreboard("my_test_scoreboard")

    # Start the scoreboard's comparison thread
    my_scoreboard.start()

    # Simulate receiving actual and expected transactions
    # In a real test, these would come from monitors and reference models

    # Simulate some matching transactions
    my_scoreboard.write_actual(Transaction("data_A"))
    my_scoreboard.write_expected(Transaction("data_A"))

    my_scoreboard.write_actual(Transaction(123))
    my_scoreboard.write_expected(Transaction(123))

    # Simulate a mismatch
    my_scoreboard.write_actual(Transaction("data_B"))
    my_scoreboard.write_expected(Transaction("data_C")) # Mismatch here

    # Simulate another mismatch
    my_scoreboard.write_actual(Transaction([1, 2, 3]))
    my_scoreboard.write_expected(Transaction([1, 2, 4])) # Another mismatch

    # Simulate more matching transactions
    my_scoreboard.write_actual(Transaction({"key": "value"}))
    my_scoreboard.write_expected(Transaction({"key": "value"}))

    # Allow some time for the comparison thread to process
    time.sleep(0.5)

    # Stop the scoreboard
    my_scoreboard.stop()

    # Generate and print the report to the console
    print("--- Reporting to Console ---")
    test_status_console = my_scoreboard.report()
    print(f"Final test status (Console): {'PASSED' if test_status_console else 'FAILED'}")


    # Generate the report and save it to a file
    report_filename = "scoreboard_report_with_details.txt"
    print(f"\n--- Reporting to File: {report_filename} ---")
    test_status_file = my_scoreboard.report(output_file=report_filename)
    print(f"Final test status (File): {'PASSED' if test_status_file else 'FAILED'}")

    # Generate an HTML report
    html_report_filename = "scoreboard_report.html"
    print(f"\n--- Reporting to HTML File: {html_report_filename} ---")
    test_status_html = my_scoreboard.report(output_file=html_report_filename, format='html')
    print(f"Final test status (HTML): {'PASSED' if test_status_html else 'FAILED'}")

    # Example with no comparisons
    print("\n--- Testing empty scoreboard ---")
    empty_scoreboard = Scoreboard("empty_scoreboard")
    empty_scoreboard.start()
    time.sleep(0.1) # Give it a moment
    empty_scoreboard.stop()
    empty_test_status = empty_scoreboard.report()
    print(f"Empty test status: {'PASSED' if empty_test_status else 'FAILED'}")

