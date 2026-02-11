#!/bin/bash
set -e
cd "$(dirname "$0")"

VERSION="${1:?用法: ./release.sh v1.0.0}"
REPO="su27/voice_input"
NAME="voice_input"

echo "=== 发布 ${VERSION} ==="

# 确保工作区干净
if [ -n "$(git status --porcelain)" ]; then
    echo "[错误] 工作区有未提交的更改"
    exit 1
fi

# 打 tag
echo "[1/4] 打 tag ${VERSION}..."
git tag -a "${VERSION}" -m "Release ${VERSION}"
git push origin "${VERSION}"

# 打包
echo "[2/4] 打包..."
TMPDIR=$(mktemp -d)
ARCHIVE="${TMPDIR}/${NAME}-${VERSION}.zip"
git archive --format=zip --prefix="${NAME}/" -o "${ARCHIVE}" "${VERSION}"

# 创建 release
echo "[3/4] 创建 GitHub Release..."
gh release create "${VERSION}" "${ARCHIVE}" \
    --repo "${REPO}" \
    --title "${VERSION}" \
    --generate-notes

rm -rf "${TMPDIR}"

echo "[4/4] 完成！"
echo "https://github.com/${REPO}/releases/tag/${VERSION}"
