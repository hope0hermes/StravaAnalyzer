# Version Management Guide

This project uses automated version management with Conventional Commits and GitHub Actions.

## How It Works

When you merge a PR to `main`, the Release workflow automatically:
1. Analyzes commit messages to determine version bump type
2. Bumps the version using `hatch version`
3. Updates `CHANGELOG.md`
4. Creates a git tag
5. Creates a GitHub Release

## Commit Message Format

Use **Conventional Commits** format in your commit messages:

### Version Bumps

| Commit Prefix | Version Bump | Example |
|---------------|--------------|---------|
| `feat:` or `feature:` | **Minor** (1.0.0 → 1.1.0) | `feat: add heart rate zones` |
| `fix:` or `bugfix:` | **Patch** (1.0.0 → 1.0.1) | `fix: correct power calculation` |
| `feat!:` or `BREAKING CHANGE:` | **Major** (1.0.0 → 2.0.0) | `feat!: redesign API` |
| Other (`chore:`, `docs:`, `style:`, `test:`) | **No bump** | `chore: update dependencies` |

### Examples

```bash
# Bug fix → Patch version (1.0.0 → 1.0.1)
git commit -m "fix: correct TSS calculation for short activities"

# New feature → Minor version (1.0.0 → 1.1.0)
git commit -m "feat: add support for running pace metrics"

# Breaking change → Major version (1.0.0 → 2.0.0)
git commit -m "feat!: change Settings API to use dataclasses"

# No version change
git commit -m "docs: update README with examples"
git commit -m "chore: update dependencies"
git commit -m "ci: fix GitHub Actions workflow"
```

## Workflow

### Normal Development

1. Create a feature branch:
   ```bash
   git checkout -b feature/add-new-metric
   ```

2. Make changes and commit with conventional format:
   ```bash
   git add .
   git commit -m "feat: add decoupling index metric"
   ```

3. Push and create PR:
   ```bash
   git push origin feature/add-new-metric
   ```

4. Merge PR to `main` via GitHub UI

5. **Automatic**: The Release workflow runs and:
   - Bumps version to 1.1.0 (because of `feat:`)
   - Updates CHANGELOG
   - Creates tag v1.1.0
   - Creates GitHub Release

### Multiple Commits in One PR

The workflow looks at **all commits** in the PR:
- If ANY commit has `feat:` → Minor bump
- If ANY commit has `feat!:` or `BREAKING CHANGE:` → Major bump
- If only `fix:` commits → Patch bump

### Manual Version Bump (Optional)

If you need to manually bump the version:

```bash
# Bump version locally
hatch version patch   # or minor, major

# Commit the change
git add src/strava_analyzer/__init__.py
git commit -m "chore: bump version to 1.0.1"

# Push to main (if you have direct push access)
git push origin main
```

## Skipping Release

If you merge a commit that shouldn't trigger a release, use these prefixes:
- `chore:` - Maintenance tasks
- `docs:` - Documentation only
- `style:` - Code formatting
- `test:` - Adding tests
- `ci:` - CI/CD changes

## Checking Current Version

```bash
# Using hatch
hatch version

# Using Python
python -c "import strava_analyzer; print(strava_analyzer.__version__)"
```

## Tips

1. **Use clear, descriptive commit messages** - They appear in the CHANGELOG
2. **One feature per commit** - Makes it easier to track changes
3. **Squash related commits** in PRs - Keep main branch history clean
4. **The workflow won't run on PRs** - Only when merged to main

## Troubleshooting

**Q: Version didn't bump after merge?**
A: Check commit messages follow conventional format. Only `feat:`, `fix:`, and breaking changes trigger bumps.

**Q: Wrong version bump?**
A: The workflow uses the highest severity commit. A single `feat!:` overrides all other commits.

**Q: How to do a manual release?**
A: Manually run the Release workflow from GitHub Actions tab → Release → Run workflow.
