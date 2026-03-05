import sys
import os

# Add workspace path to ensure dynamic import works
sys.path.append('/home/chrisj/gemini_agents/workspace/20260305_080344/')

try:
    from lib.heartbeat_parser import parse_heartbeat
    
    print("Parser module successfully imported.")
    
    # Execute the parser
    tasks = parse_heartbeat()
    
    # --- Report Generation ---
    
    REPORT_PATH = '/home/chrisj/gemini_agents/workspace/20260305_080344/PROJECT_SUMMARY.md'
    source_file = '/home/chrisj/gemini_agents/core/HEARTBEAT.md'
    
    report_content = "# Project Execution Summary\n\n"
    report_content += f"## Heartbeat Analysis ({source_file})\n\n"
    
    if not os.path.exists(source_file):
        report_content += "**ERROR:** Source file not found at path: {source_file}\n"
        errors = 1
        processed = 0
    else:
        processed = len(tasks)
        errors = 0 # Assume no parsing errors if file was read
        
        if processed == 0:
            report_content += "**SUCCESS:** No unchecked tasks (lines starting with \'- [ ]\') were found in the heartbeat file.\n"
        else:
            report_content += f"**PROCESSED:** Found {processed} unchecked tasks.\n\n"
            report_content += "### Unchecked Tasks:\n"
            for i, task in enumerate(tasks, 1):
                report_content += f"{i}. [ ] {task['task_description']} (Source: {task['source_file']})\n"
                
    report_content += "\n---\n\n## Execution Metrics\n"
    report_content += f"- Total Tasks Found: {processed}\n"
    report_content += f"- Errors Encountered: {errors}\n"
    
    # Write the final report
    with open(REPORT_PATH, 'w') as f:
        f.write(report_content)
        
    print(f"\n[FINAL_REPORT_GENERATED]: {REPORT_PATH}")
    print(f"[SUMMARY_DATA]: Processed={processed}, Errors={errors}")

except ImportError as e:
    print(f"FATAL ERROR: Could not import heartbeat_parser or its dependencies: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"AN UNEXPECTED ERROR OCCURRED during execution: {e}", file=sys.stderr)
    sys.exit(1)

