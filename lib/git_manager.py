import subprocess

def git_branch(branch_name):
    """Creates and switches to a new optimization branch."""
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)

def git_stage_and_commit(message):
    """Stages all changes and commits them."""
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", message], check=True)

def git_prepare_merge(target_branch="main", source_branch=None):
    """Prepares the branch for merge by pulling latest changes."""
    current_branch = source_branch or subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    subprocess.run(["git", "checkout", target_branch], check=True)
    subprocess.run(["git", "pull", "origin", target_branch], check=True)
    subprocess.run(["git", "merge", current_branch], check=True)