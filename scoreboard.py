import inspect
import queue
import threading
import time
import sys # Import sys to write to stdout and stderr

# Define a simple Transaction class for demonstration purposes
# In a real testbench, this would represent the data being monitored
class Transaction:
    """Represents a single data transaction or event."""
    def __init__(self, data, timestamp=None):
        self.data = data
        self.timestamp = timestamp if timestamp is not None else time.time()
        try:
            # Get the frame of the caller
            caller_frame = inspect.currentframe().f_back
            # Get the line number from the frame
            self.line = caller_frame.f_lineno
        except Exception:
            self.line = None

    def __eq__(self, other):
        """Equality check for comparison."""
        if not isinstance(other, Transaction):
            return False
        # Simple data comparison; more complex logic might be needed
        # depending on the actual transaction data structure.
        return self.data == other.data

    def __repr__(self):
        """String representation for debugging/reporting."""
        return f"Transaction(data={self.data}, timestamp={self.timestamp:.4f}, line={self.line})"

class Scoreboard:
    """
    A simple scoreboard class for comparing actual vs. expected data streams.

    Inspired by verification scoreboard concepts. It uses queues to handle
    asynchronous data arrival and performs comparisons.
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
        # Flag to indicate if the scoreboard is actively comparing
        self._running = False
        # Thread for performing comparison in the background
        self._comparison_thread = None
        # Event to signal the comparison thread to stop
        self._stop_event = threading.Event()

        print(f"[{self.name}] Scoreboard initialized.")

    def write_actual(self, transaction: Transaction):
        """
        Receives an actual transaction from the test environment.

        Args:
            transaction (Transaction): The actual transaction object.
        """
        if not isinstance(transaction, Transaction):
            print(f"[{self.name}] Warning: Received non-Transaction object for actual data.")
            return
        self._actual_queue.put(transaction)
        print(f"[{self.name}] Received actual: {transaction}")

    def write_expected(self, transaction: Transaction):
        """
        Receives an expected transaction from a reference model.

        Args:
            transaction (Transaction): The expected transaction object.
        """
        if not isinstance(transaction, Transaction):
            print(f"[{self.name}] Warning: Received non-Transaction object for expected data.")
            return
        self._expected_queue.put(transaction)
        print(f"[{self.name}] Received expected: {transaction}")

    def _compare_transactions(self):
        """
        Internal method to continuously compare transactions from the queues.
        Runs in a separate thread.
        """
        print(f"[{self.name}] Comparison thread started.")
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
                    print(f"[{self.name}] MATCH: Actual={actual_txn}, Expected={expected_txn}")
                else:
                    print(f"[{self.name}] MISMATCH: Actual={actual_txn}, Expected={expected_txn}")

            except queue.Empty:
                # If one queue is empty, wait a bit before checking again
                # This handles cases where data arrives asynchronously
                time.sleep(0.01)
            except Exception as e:
                print(f"[{self.name}] Error during comparison: {e}")
                # In case of error, mark as mismatch for safety
                with self._comparison_lock:
                     self._results.append(False)
                     # Store error details as a mismatch
                     self._mismatches_details.append({
                         "error": str(e),
                         "actual": actual_txn, # May be None
                         "expected": expected_txn # May be None
                     })


        print(f"[{self.name}] Comparison thread stopped.")


    def start(self):
        """Starts the background comparison thread."""
        if not self._running:
            self._running = True
            self._stop_event.clear()
            self._comparison_thread = threading.Thread(target=self._compare_transactions)
            self._comparison_thread.start()
            print(f"[{self.name}] Scoreboard started.")
        else:
            print(f"[{self.name}] Scoreboard is already running.")

    def stop(self):
        """Stops the background comparison thread and waits for it to finish."""
        if self._running:
            print(f"[{self.name}] Stopping scoreboard...")
            self._stop_event.set() # Signal thread to stop
            if self._comparison_thread and self._comparison_thread.is_alive():
                 self._comparison_thread.join(timeout=5) # Wait for thread to finish
                 if self._comparison_thread.is_alive():
                     print(f"[{self.name}] Warning: Comparison thread did not stop gracefully.")
            self._running = False
            print(f"[{self.name}] Scoreboard stopped.")
        else:
            print(f"[{self.name}] Scoreboard is not running.")


    def report(self, output_file=None):
        """
        Generates a report based on the comparison results and optionally writes it to a file.
        Includes details for any mismatches found.

        Args:
            output_file (str, optional): The path to a file where the report should be saved.
                                         If None, the report is only printed to the console.

        Returns:
            bool: True if all comparisons were successful, False otherwise.
        """
        # Determine where to write the output (file or console)
        if output_file:
            try:
                f = open(output_file, 'w')
            except IOError as e:
                print(f"[{self.name}] Error opening output file {output_file}: {e}", file=sys.stderr)
                f = sys.stdout # Fallback to console if file opening fails
        else:
            f = sys.stdout # Default to console output

        def write_line(line):
            """Helper function to write to both file (if open) and console."""
            print(line, file=f)
            if f != sys.stdout:
                 print(line, file=sys.stdout) # Also print to console if writing to console


        write_line(f"\n[{self.name}] --- Scoreboard Report ---")
        if self.test_description:
            write_line(f"Test Description: {self.test_description}")
        total_comparisons = len(self._results)
        mismatches = len(self._mismatches_details) # Use the detailed list count
        matches = total_comparisons - mismatches

        write_line(f"Total comparisons: {total_comparisons}")
        write_line(f"Matches: {matches}")
        write_line(f"Mismatches: {mismatches}")

        success = (mismatches == 0 and total_comparisons > 0) # Consider success only if comparisons happened and no mismatches

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
             success = False # No comparisons means no success
        else:
            write_line(f"[{self.name}] TEST FAILED: Mismatches detected.")

        write_line(f"[{self.name}] ---------------------------\n")

        # Close the file if it was opened
        if output_file and f != sys.stdout:
            f.close()

        return success

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

    # Example with no comparisons
    print("\n--- Testing empty scoreboard ---")
    empty_scoreboard = Scoreboard("empty_scoreboard")
    empty_scoreboard.start()
    time.sleep(0.1) # Give it a moment
    empty_scoreboard.stop()
    empty_test_status = empty_scoreboard.report()
    print(f"Empty test status: {'PASSED' if empty_test_status else 'FAILED'}")

