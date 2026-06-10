#!/bin/bash
CURRENT_DIR=$(basename "$PWD")

if [ "$CURRENT_DIR" != "backend" ]; then
    echo "Current directory is $CURRENT_DIR. Switching to /backend..."
    cd ../../backend || { echo "Error: Could not find backend directory"; exit 1; }
else
    echo "Already in backend directory. Proceeding..."
fi

cleanup () {
    echo "--- Tearing down container ---"
    docker compose down
}

trap cleanup EXIT

TARGET_TESTS="${@:-tests/}"

echo "--- Spinning up container ---"
docker compose up --build -d --wait

echo "--- Running tests: $TARGET_TESTS ---"
docker compose exec backend pytest $TARGET_TESTS

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Success: All tests passed."
else
    echo "❌ Failure: Tests failed with exit code $TEST_EXIT_CODE."
fi

exit $TEST_EXIT_CODE
