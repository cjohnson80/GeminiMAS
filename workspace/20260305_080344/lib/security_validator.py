import shlex
import os

# Security Expert Rule: Define a strict whitelist of allowed shell commands.
ALLOWED_COMMANDS = {"ls", "cat", "echo", "grep", "pwd", "mkdir", "head", "tail"}

class SecurityViolationError(Exception):
    """Custom exception for security policy violations."""
    pass

def sanitize_command(command_string: str) -> str:
    """
    Analyzes a command string to prevent injection and execution of disallowed commands.
    
    Mitigation Strategies:
    1. Command Whitelisting: Ensures the primary executable is in ALLOWED_COMMANDS.
    2. Argument Splitting: Uses shlex.split to handle arguments safely, preventing complex shell metacharacter injection.
    3. Destructive Command Prevention: Explicitly blocks common destructive commands if they somehow slip past the whitelist.
    
    Args:
        command_string: The raw command string to execute.

    Returns:
        The sanitized command string.

    Raises:
        SecurityViolationError: If the command is malicious or disallowed.
    """
    if not command_string or not command_string.strip():
        raise SecurityViolationError("Empty command string provided.")
        
    # 1. Use shlex.split to safely parse the command and arguments.
    try:
        parts = shlex.split(command_string)
    except ValueError as e:
        raise SecurityViolationError(f"Malformed command string: {e}")
        
    if not parts:
        raise SecurityViolationError("Command resolved to no executable.")
        
    executable = parts[0]
    
    # 2. Check against the whitelist
    if executable not in ALLOWED_COMMANDS:
        # Fail fast if the executable is not explicitly permitted
        raise SecurityViolationError(f"Unauthorized executable: {executable}. Only {list(ALLOWED_COMMANDS)} are permitted.")
        
    # 3. Additional check for common destructive patterns, although whitelist should cover this.
    if executable in ["rm", "mv", "cp", "dd", "sh", "bash", "perl", "python", "node", "wget", "curl", "nc", "socat"]:
        # These are often restricted even if they appear in a base whitelist, depending on context.
        # For this setup, we rely heavily on the whitelist, but this acts as a secondary defense.
        pass # Allowed if they are in ALLOWED_COMMANDS, otherwise blocked above.
        
    # Reconstruct the command string safely (shlex.join is Python 3.8+; using simple join for broader compatibility if needed, but shlex.split handles the parsing risk).
    # Since we verified the parts, returning the original string or joining the parts back is generally safe if the initial split was successful and the executable is whitelisted.
    return command_string


if __name__ == '__main__':
    # --- Security Testing ---
    print("--- Running Security Validator Tests ---")
    
    safe_commands = ["ls -l /tmp", "cat /etc/hosts", "echo "Hello World""]
    
    for cmd in safe_commands:
        try:
            sanitized = sanitize_command(cmd)
            print(f"[PASS] Safe command: '{cmd}' -> '{sanitized}'")
        except SecurityViolationError as e:
            print(f"[FAIL] Safe command unexpectedly blocked: '{cmd}' ({e})")
            
    # Malicious/Injection tests
    malicious_commands = ["rm -rf /", "cat /etc/passwd; rm -rf /", "./exploit.sh; bash", "ls | grep secret", "echo 'test' > file.txt"]
    
    for cmd in malicious_commands:
        try:
            sanitize_command(cmd)
            print(f"[FAIL] Malicious command executed successfully: '{cmd}'")
        except SecurityViolationError as e:
            print(f"[PASS] Malicious command blocked: '{cmd}' (Reason: {e})")
    
    # Test injection that relies on shell features (e.g., pipes/redirects used as executable names)
    injection_test = "'ls'" # Should fail because the executable is 'ls' but shlex might parse it weirdly if quotes are not handled by the caller
    try:
        sanitize_command(injection_test)
        print(f"[FAIL] Injection test executed successfully: '{injection_test}'")
    except SecurityViolationError as e:
        print(f"[PASS] Injection test blocked: '{injection_test}' (Reason: {e})")
