# Verify Git hosting protection

Repository-local checks cannot independently restrain an agent with authority to
rewrite CI, approve its own changes and bypass protection. Use separate actor
permissions and protected review of policy, workflow and ownership files.
Doctor is read-only and reports missing/unavailable settings as blocked.

## GitHub

Require PRs, the exact `harness-gate` status check, an up-to-date branch and
review of the latest push by another actor. Dismiss stale approvals and require
Code Owner approval. Protect the harness specification, generated runner, CI,
test configuration and CODEOWNERS itself with real owner identities. Apply
protection to administrators and avoid bypass allowances for the coding agent.

The aggregate workflow explicitly validates every required report because GitHub
can accept a skipped/neutral check. Ensure the expected check producer is trusted.
Doctor currently inspects classic branch protection; ruleset-only protection is
reported as unverified rather than assumed equivalent. Verify rulesets manually
until a dedicated ruleset adapter is implemented.

Official references:
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners

## GitLab

Require successful pipelines; do not allow merging skipped pipelines. Disallow
direct push and force push under every matching exact/wildcard protection rule.
Keep MR merge permission with authorized reviewers. Require fresh independent
approvals and protect policy/CI ownership where the GitLab tier permits it.

Required approvals and Code Owner features require Premium/Ultimate. GitLab Free
optional approvals do not enforce review. Report this boundary explicitly and
keep agent credentials below the role allowed to merge policy changes. A local
CODEOWNERS file alone does not make review mandatory.

Doctor reads project settings, protected branch rules and available approval
settings. It cannot certify unrelated instance/group policies, actor permissions,
or an unqueried rules page. More than one page of branch protection must be
queried before declaring full protection.

Official references:
- https://docs.gitlab.com/user/project/merge_requests/approvals/
- https://docs.gitlab.com/user/project/repository/branches/protection_rules/

## Live acceptance

Use an explicitly authorized disposable repository for each provider. Exercise
a successful PR/MR, failed command, skipped/missing job, stale report and a policy
change requiring another actor's approval. Confirm the server blocks merging.
Do not attempt destructive bypass demonstrations against a real main branch.
