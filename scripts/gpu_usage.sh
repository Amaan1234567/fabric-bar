#!/bin/bash

# Get GPU utilization from nvidia-smi
gpu_utilization=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)

# Create and echo JSON output
echo "{\"class\": \"data\", \"text\": $gpu_utilization}"
