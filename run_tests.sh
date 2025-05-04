#!/bin/bash

# Start the Firebase emulator in the background
firebase emulators:start --only firestore &
EMULATOR_PID=$!

# Wait for the emulator to start
sleep 5

# Run the tests
pytest "$@"

# Store the exit code of pytest
TEST_EXIT_CODE=$?

# Kill the emulator
kill $EMULATOR_PID

# Exit with the test's exit code
exit $TEST_EXIT_CODE 