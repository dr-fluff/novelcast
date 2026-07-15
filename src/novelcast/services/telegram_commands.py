# novelcast/services/telegram_commands.py
#
# Central registry of Telegram bot commands.
# Add a new command by:
#   1. Adding a KEY + COMMAND constant below
#   2. Adding it to TELEGRAM_COMMANDS
#   3. Adding a matching handler in TelegramService._COMMAND_HANDLERS

STATUS_KEY = 1
STATUS_COMMAND = "/status"

STORIES_KEY = 2
STORIES_COMMAND = "/stories"

DOWNLOAD_KEY = 3
DOWNLOAD_COMMAND = "/download"

UPDATE_KEY = 4
UPDATE_COMMAND = "/update"

HELP_KEY = 5
HELP_COMMAND = "/help"

TELEGRAM_COMMANDS = {
    STATUS_KEY: STATUS_COMMAND,
    STORIES_KEY: STORIES_COMMAND,
    DOWNLOAD_KEY: DOWNLOAD_COMMAND,
    UPDATE_KEY: UPDATE_COMMAND,
    HELP_KEY: HELP_COMMAND,
}

# Shown in Telegram's "/" autocomplete menu via setMyCommands.
# Keep each under ~256 chars (Telegram's limit).
COMMAND_DESCRIPTIONS = {
    STATUS_KEY: "Check if NovelCast is running",
    STORIES_KEY: "List recent stories",
    DOWNLOAD_KEY: "Download a story from a URL",
    UPDATE_KEY: "Check all stories for new chapters",
    HELP_KEY: "Show available commands",
}

# Reverse lookup: command string -> key, used to resolve incoming text
COMMAND_KEYS_BY_TEXT = {command: key for key, command in TELEGRAM_COMMANDS.items()}


def build_bot_commands_payload() -> list[dict]:
    """Build the list Telegram's setMyCommands API expects.

    Telegram wants the leading "/" stripped from each command name.
    """
    return [
        {"command": command.lstrip("/"), "description": COMMAND_DESCRIPTIONS.get(key, "")}
        for key, command in TELEGRAM_COMMANDS.items()
    ]

# Optional argument hint for commands that take one, shown only in /help
# text (Telegram's setMyCommands menu doesn't support argument placeholders).
COMMAND_USAGE = {
    DOWNLOAD_KEY: "<url>",
}


def build_help_text() -> str:
    """Build the /help message body: one line per command with its
    usage hint and description, formatted for Telegram's Markdown parse mode."""
    lines = ["*NovelCast bot commands*", ""]
    for key, command in TELEGRAM_COMMANDS.items():
        usage = COMMAND_USAGE.get(key)
        label = f"{command} {usage}" if usage else command
        description = COMMAND_DESCRIPTIONS.get(key, "")
        lines.append(f"`{label}` — {description}" if description else f"`{label}`")
    return "\n".join(lines)
