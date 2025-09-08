# GIL Enabler Test Extension

This directory contains a C extension module used for testing GIL detection functionality.

## Purpose

The `gil_[enable|disable]` extension module is designed to trigger actual GIL enabling behavior in
free-threaded Python builds, replacing the previous approach that used `warnings.warn()`
to simulate the warning message.

## Building

To build the extension in-place for testing:

```bash
python setup.py build_ext -i
```

## Usage in Tests

The extension module is built and imported in the test files to trigger actual GIL enabling
behavior, which allows for more realistic testing of the GIL detection feature.
