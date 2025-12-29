#!/bin/bash

# Create test files
echo "This is the first test document for analysis." > /tmp/test_doc1.txt
echo "This is the second document with different content." > /tmp/test_doc2.txt
echo "Third test file with more information." > /tmp/test_doc3.txt

# Prepare the configs JSON
CONFIGS='[
  {
    "id": "gpt4_001",
    "provider": "openai",
    "model": "gpt-4",
    "system": "You are a helpful assistant."
  }
]'

# Send multipart request with multiple attachments
echo "Testing with multiple attachments..."
curl -X POST http://localhost:8000/runs \
  -F "message=Analyze these documents and provide a summary" \
  -F "configs=$CONFIGS" \
  -F "max_parallel=10" \
  -F "attachments=@/tmp/test_doc1.txt" \
  -F "attachments=@/tmp/test_doc2.txt" \
  -F "attachments=@/tmp/test_doc3.txt" \
  -w "\nStatus: %{http_code}\n"

# Cleanup
rm /tmp/test_doc1.txt /tmp/test_doc2.txt /tmp/test_doc3.txt

echo "Test complete!"
