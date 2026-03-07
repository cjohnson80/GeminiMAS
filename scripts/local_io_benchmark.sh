#!/bin/bash
# I/O Performance Benchmark Script

FILE_SIZE_MB=500
TEST_FILE="workspace/default/io_benchmark_test_file.bin"

echo "[1/4] Generating $FILE_SIZE_MB MB of random data..."
# Use dd to create a large file filled with random data (this is I/O intensive)
dd if=/dev/urandom of=$TEST_FILE bs=1M count=$FILE_SIZE_MB status=progress || { echo "Data generation failed."; exit 1; }

echo "[2/4] Benchmarking Write Speed..."
START_TIME=$(date +%s.%N)
# Re-write the file to ensure we measure the actual write speed to disk
dd if=/dev/urandom of=$TEST_FILE bs=1M count=$FILE_SIZE_MB status=none
END_TIME=$(date +%s.%N)
WRITE_DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
WRITE_SPEED=$(echo "scale=2; ($FILE_SIZE_MB / $WRITE_DURATION) / 1024 / 1024" | bc -l)
echo "Write Speed: $WRITE_SPEED GB/s (Duration: $WRITE_DURATION s)"

echo "[3/4] Benchmarking Read Speed..."
START_TIME=$(date +%s.%N)
# Read the file into /dev/null to measure raw read throughput
dd if=$TEST_FILE of=/dev/null bs=1M status=none
END_TIME=$(date +%s.%N)
READ_DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
READ_SPEED=$(echo "scale=2; ($FILE_SIZE_MB / $READ_DURATION) / 1024 / 1024" | bc -l)
echo "Read Speed: $READ_SPEED GB/s (Duration: $READ_DURATION s)"

echo "[4/4] Cleanup..."
rm -f $TEST_FILE

echo "Benchmark Complete."