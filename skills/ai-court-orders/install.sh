#!/usr/bin/env bash
# Install the ai-court-orders Claude Code skill.
# Downloads SKILL.md + the bundled CLI into your Claude skills directory.
#
#   curl -fsSL https://raw.githubusercontent.com/legalrealist/AI-orders-explorer/main/skills/ai-court-orders/install.sh | bash
#
# Override the install location with CLAUDE_SKILLS_DIR (default: ~/.claude/skills).
set -euo pipefail

RAW="https://raw.githubusercontent.com/legalrealist/AI-orders-explorer/main"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/ai-court-orders"

command -v python3 >/dev/null 2>&1 || { echo "error: python3 is required" >&2; exit 1; }

echo "Installing ai-court-orders skill → $DEST"
mkdir -p "$DEST"
curl -fsSL "$RAW/skills/ai-court-orders/SKILL.md" -o "$DEST/SKILL.md"
curl -fsSL "$RAW/scripts/orders_cli.py"           -o "$DEST/orders_cli.py"
chmod +x "$DEST/orders_cli.py"

echo "Done. Restart Claude Code (or /skills reload), then ask:"
echo "  \"which courts sanction attorneys most for AI misuse?\""
echo "or invoke it directly: /ai-court-orders <question>"
