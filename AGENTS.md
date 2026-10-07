# OOXML Client development

Write source, documentation, help and errors in English. Keep the client free of
Office parsing, editing algorithms, private source and private Git dependencies.
Use the runtime's existing operation names, errors and evidence contracts.

Run project tests on the authorized LAN host. Test subprocess failures and real
runtime workflows; mock responses alone do not prove document behavior. Keep
source files below 300 lines and functions below 50 lines. Store generated
packages and evidence outside source checkouts.

Do not change the commercial runtime's licenses or upstream notices. This
repository's license covers its own client implementation only.

## Public commit identity

- Use the GitHub privacy identity `iamtouchskyer
  <14212314+iamtouchskyer@users.noreply.github.com>` for the repository owner's
  author and committer fields. Never use a personal email address.
- Before committing or pushing, verify author, committer and tagger identities,
  commit-message trailers, and newly added content. Use noreply addresses for
  attribution; do not replace other contributors' identities without permission.
- Set this identity in repository-local Git configuration. Do not rely on a
  global configuration that may expose a personal address.
- After a privacy history rewrite, use the rewritten history. Do not merge or
  force-push old refs back into public branches or tags. Keep recovery bundles
  private and migrate live commit pins using the recorded identity mapping.
- GitHub merge and squash commits also need an explicit private author email:
  pass `--author-email 14212314+iamtouchskyer@users.noreply.github.com` to
  `gh pr merge`, then inspect the resulting author and committer. Repository-local
  Git configuration does not control commits created by GitHub.
- If GitHub rejects the noreply address, stop that merge attempt. Never retry
  with a personal email or an implicit default. Resolve the hosted identity, or
  use an explicitly authorized local merge with verified anonymous metadata and
  the repository's required checks; preserve branch protection.
- GitHub can synthesize `refs/pull/*/merge` using the account email, independently
  of local Git identity and `gh pr merge --author-email`. Before opening or
  updating the owner's public PRs, confirm **Keep my email addresses private**
  is enabled at <https://github.com/settings/emails>, then inspect the generated
  merge metadata. If privacy is unverified or the address still appears, report
  the account-level blocker and avoid creating more such commits. Use only an
  already authorized publishing route that retains the required checks.
