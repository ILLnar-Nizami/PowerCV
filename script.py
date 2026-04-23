import os
import subprocess

# Define the GitHub repository and owner
REPO_OWNER = "illnar"
REPO_NAME = "PowerCV"

# Define the GitHub CLI commands to retrieve open Pull Requests
GET_OPEN_PRS_CMD = f"gh api /repos/{REPO_OWNER}/{REPO_NAME}/pulls?state=open&sort=updated&direction=desc"

# Define the GitHub CLI commands to retrieve comments and status checks for a Pull Request
GET_PR_COMMENTS_CMD = f"gh api /repos/{REPO_OWNER}/{REPO_NAME}/pulls/{}/comments"
GET_PR_STATUS_CHECKS_CMD = f"gh api /repos/{REPO_OWNER}/{REPO_NAME}/pulls/{}/status"

# Define the GitHub CLI commands to apply necessary code fixes locally
GET_REPO_CMD = f"gh api /repos/{REPO_OWNER}/{REPO_NAME}/repository"
GET_TREE_CMD = f"gh api /repos/{REPO_OWNER}/{REPO_NAME}/pulls/{}/commits/{}"
APPLY_PATCH_CMD = f"mkdir -p {REPO_OWNER}/{REPO_NAME}/{}/ && git add {REPO_OWNER}/{REPO_NAME}/{}/ && git commit -m \"tool_graph: \" && git push"

# Loop through each Pull Request and retrieve comments and status checks
for pr in get_openprs():
    pr_num = pr['number']
    pr_url = pr['url']
    if pr['review_comments'] or pr['status_check_rollout']:
        # Retrieve comments and status checks for the Pull Request
        comments = get_pr_comments(pr_num)
        status_checks = get_pr_status_checks(pr_num)
        # Apply necessary code fixes locally
        repo = get_repo()
        tree = get_tree(pr_num, pr['sha'])
        repository_path = f"{REPO_OWNER}/{REPO_NAME}/{pr_num}"
        execute(APPLY_PATCH_CMD.format(pr_num, repository_path))