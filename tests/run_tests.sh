#!/bin/bash
# Integration test runner

echo "Running integration tests..."
cd tests
python3 -m pytest test_integration.py -v
cd ..

echo ""
echo "Tests complete!"
