# Python Scoreboard

A simple Python-based scoreboard for data verification, inspired by concepts used in hardware verification testbenches. This scoreboard compares two streams of data (actual vs. expected) and reports any mismatches.

## Features

- Asynchronous data handling using queues.
- Thread-safe comparison mechanism.
- Detailed reporting of matches and mismatches, including the line number of the transaction.
- Test descriptions are automatically included in the report.
- Ability to write reports to a file or print to the console.
- HTML reporting for a more structured and readable output.

## Why Use This Scoreboard?

While standard testing frameworks like `unittest` are excellent for checking the final output of a function, this scoreboard is designed for a different verification paradigm, particularly for **dynamic, concurrent, or stream-based systems**.

Here are the key scenarios where this implementation provides a significant advantage:

1.  **Asynchronous Verification**: The scoreboard runs in a separate thread, allowing it to monitor and compare data streams from your system-under-test (SUT) in real-time, which is ideal for testing network services, multi-threaded applications, or data pipelines where results arrive over time.

2.  **Data Stream and Sequence Validation**: It is built to verify continuous, ordered streams of data. It compares `Transaction` objects one by one as they are received, immediately flagging any deviation in a long sequence.

3.  **Decoupled Architecture**: It separates the "checker" from the "stimulus" and the "SUT." This allows you to build a more modular and reusable test environment where the scoreboard's only job is to compare outputs from the SUT and a reference model.

4.  **Real-time Mismatch Reporting**: In long-running tests, you don't have to wait until the end to discover a failure. The scoreboard prints `MISMATCH` to the console as soon as it occurs, making it much faster to debug complex systems.

In short, think of `unittest` as a **final exam** (checking the final answer) and this scoreboard as a **live referee** (watching the entire process and making calls in real-time).

## The `Transaction` Class

The `Transaction` class is a flexible container for the data you want to verify. It is designed to be adaptable for both simple and complex data structures.

-   **Simple Data**: For basic data types like strings, numbers, or dictionaries, you can use the `Transaction` class directly.
-   **Complex Data**: For more complex data structures, you can extend the `Transaction` class and override the `__eq__` method to implement custom comparison logic. This is useful when you only need to compare specific fields in a larger data object.

## Usage

The main script `scoreboard.py` can be run directly to see a demonstration of the scoreboard in action.

```bash
python scoreboard.py
```

This will output the results of a predefined test case with both matching and mismatching transactions.

### Reporting

The scoreboard can generate reports in two formats:

-   **Text**: A plain text report printed to the console or saved to a file.
-   **HTML**: A structured HTML report that is easy to read and share.

To generate an HTML report, specify an output file with an `.html` extension in the `report` method.

## Testing

A test suite is provided in `test_scoreboard.py` using Python's built-in `unittest` framework. To run the tests, execute the following command from the root directory:

```bash
python -m unittest test_scoreboard.py
```
