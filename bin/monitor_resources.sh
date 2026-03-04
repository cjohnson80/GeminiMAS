#!/bin/bash
while true; do echo "$(date +%T) | CPU: $(top -bn1 | grep "Cpu(s)" | awk "{print \$2}")% | RAM: $(free -m | awk "/Mem:/ {print \$3}")MB" >> ~/GeminiMAS_Repo/logs/resource_monitor.log; sleep 5; done
