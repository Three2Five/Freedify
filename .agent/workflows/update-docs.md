---
description: How to finalize changes with documentation updates
---

# Documentation Update Workflow

After making any code changes, fixes, or new features, **always** update the documentation before completing the task.

## Checklist

### 1. Update CHANGELOG.md
- Add changes under `[Unreleased]` section, or create a new version section if releasing
- Use standard format:
  - `### Added` - For new features
  - `### Changed` - For changes in existing functionality
  - `### Fixed` - For bug fixes
  - `### Removed` - For removed features
- Include brief, user-facing descriptions of each change

### 2. Update README.md
- Update the `*Last updated:*` date at the top
- Add new features to the relevant sections in the Features list
- Update any configuration/setup instructions if needed
- Add new keyboard shortcuts if applicable

### 3. Version Bump (if releasing)
- CHANGELOG: Create new version header with date (e.g., `## [1.2.0] - 2026-01-22`)
- Update app.js version string if present
- Consider updating any version references in Docker/build files

## Quick Reference

**CHANGELOG location:** `CHANGELOG.md` (project root)
**README location:** `README.md` (project root)
**Date format:** `Month DD, YYYY` (e.g., January 22, 2026)
**Version format:** `[MAJOR.MINOR.PATCH]` (Semantic Versioning)

## Example CHANGELOG Entry

```markdown
## [1.2.0] - 2026-01-22

### Added
- **Feature Name**: Brief description of what it does

### Fixed
- **Bug Name**: What was broken and how it's fixed now

### Changed
- **Change Name**: What changed and why
```

> [!IMPORTANT]
> Do NOT commit code changes without updating documentation. This ensures users and contributors always have accurate information about the project.
