#!/bin/bash

set -e

VERSION=$1

if [ -z "$VERSION" ]; then
  echo "Usage: ./create_release.sh X.Y.Z"
  exit 1
fi

# Checks clean working tree
if ! git diff-index --quiet HEAD --; then
  echo "There are uncommitted changes"
  git status
  exit 1
fi

# Checks branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
  git checkout main
fi

# checks if it is ok to merge
git fetch origin && \
[ -z "$(git status --porcelain)" ] || { echo "There are uncommitted changes"; exit 1; } && \
git merge-base --is-ancestor origin/main HEAD && \
echo "OK to merge" || \
echo "Rebase or merge main first" && exit 1


# Updates main & merges
git pull origin main
git merge $BRANCH

# generating changelog
git cliff -o CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore: update changelog"

# Creates annotated tag
git tag -a "v$VERSION" -m "Release v$VERSION"

# Push branch + tag
git push origin main
git push origin "v$VERSION"

gh release create "v$VERSION" --notes "$(git cliff --latest)"

echo "✅ Release v$VERSION created successfully"
