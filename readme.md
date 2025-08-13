# Coaster of the Day Discord Bot

Automated Discord bot that posts a daily **Random Roller Coaster** entry scraped from [rcdb.com](https://rcdb.com) into any channel you configure. It also lets you manually fetch a current random coaster or a list of several consecutive random coaster picks.

## Features

- Slash commands (application commands) – no prefix clutter.
- Daily scheduled "Coaster of the Day" (COD) messages per channel at custom UTC times.
- Safe time reconfiguration: re‑running the command updates the existing schedule.
- Manual commands to pull:
  - A single fresh RCDB snapshot.
  - A list of N random coaster entries (lightweight scraping each time).
- Persistent channel scheduling stored in `cod/channels.json` (survives restarts).
- Daily regeneration of the `cod.txt` file at UTC midnight so the next send is always fresh.

## How It Works

1. On startup (`on_ready`):
   - Syncs slash commands.
   - Ensures `cod.txt` exists (creates an initial random coaster snapshot if missing).
   - Starts two background loops:
     - `daily_rcdb_gen()` – waits until the end of the current UTC day, then regenerates `cod.txt`, repeating daily.
     - `start_cod()` – loads all channel/time pairs from `cod/channels.json` and schedules a dedicated async task per channel.
2. Each channel task (managed by `CodTaskManager`) sleeps until the next scheduled time (computed in UTC) and then sends the cached `cod.txt` contents.
3. The `/cod` command lets moderators set or update the UTC time for that channel (HH:MM 24h format).
4. The `/cancelcod` command removes the channel schedule and cancels its running task.

## Commands

| Command            | Arguments                 | Permission Needed | Description                                                                            |
| ------------------ | ------------------------- | ----------------- | -------------------------------------------------------------------------------------- |
| `/rcdb`            | –                         | None              | Returns a freshly scraped random coaster summary immediately.                          |
| `/rcdblist amount` | `amount` (int)            | None              | Returns a markdown list of that many random coaster picks (one fresh scrape per loop). |
| `/cod utc_time`    | `utc_time` in `HH:MM` 24h | Manage Server     | Schedule (or reschedule) daily COD for this channel at the given UTC time.             |
| `/cancelcod`       | –                         | Manage Server     | Cancel the scheduled COD for this channel.                                             |

### Time Format

Times are interpreted as **UTC**, 24‑hour format (`HH:MM`). Example: `09:00`, `17:45`, `23:59`.

If users provide local times, remind them to convert to UTC first.

## File Overview

| File                | Purpose                                                          |
| ------------------- | ---------------------------------------------------------------- |
| `main.py`           | Bot startup, slash command definitions, lifecycle orchestration. |
| `utils.py`          | Scraping, scheduling logic, task manager, helper utilities.      |
| `cod.txt`           | Cached coaster markdown sent to channels (regenerated daily).    |
| `cod/channels.json` | Persistent mapping of channel_id -> scheduled UTC time strings.  |
| `.env` (ignored)    | Must contain `DISCORD_TOKEN=...`.                                |

## Scheduling Details

Each channel gets its own asyncio task created via `CodTaskManager.start_cod()`. The task:

1. Calculates the next execution `datetime` (if the time today already passed, it uses tomorrow).
2. Sleeps the exact remaining seconds.
3. Sends the current `cod.txt` content.
4. Loops to compute the next day.

Canceling is done by calling `task.cancel()` and removing the entry from the JSON file.

## Installation & Setup

1. Clone or copy this project into a folder.
2. Create and activate a Python 3.12+ virtual environment (already present in `env/` if you committed it, but normally you should recreate locally):

```cmd
python -m venv env
env\Scripts\activate
```

3. Install dependencies:

```cmd
pip install discord.py python-dotenv beautifulsoup4 requests
```

4. Create a `.env` file (same directory as `main.py`):

```
DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
```

5. Ensure the application commands (slash commands) are enabled for your bot in the Discord Developer Portal and the bot has the necessary privileged intents you actually use (here: message content is enabled in code, but you can disable if not needed for slash-only usage).

6. Run the bot:

```cmd
python main.py
```

7. In Discord, run `/cod 17:30` (example) in a channel to schedule daily messages.

## Permissions & Intents

The bot currently initializes with `Intents.all()` and `message_content = True`. You can harden by reducing to only guilds & messages if you don't rely on message content events elsewhere.

## Data Persistence

- `cod/channels.json` is the single source of truth for schedules.
- On restart, any channels listed are re‑scheduled automatically.
- Removing an entry manually from the file (while the bot is offline) prevents it from being re‑created.

## Error Handling & Logging

- Simple console logging via `log()` with UTC timestamps.
- If a scheduled channel is missing (bot removed permissions, channel deleted), the task logs and stops.
- Time parsing robustly validates 0 ≤ hour ≤ 23 and 0 ≤ minute ≤ 59.

## RCDB Scraping Notes

The scraper targets the `id="rrc_text"` element on the RCDB homepage. If RCDB changes layout, scraping may fail silently or produce incomplete fields. Consider adding:

- Try/except around network calls.
- HTTP timeout + fallback.
- Rate limiting if you expand usage.

## Troubleshooting

| Issue                        | Cause                              | Fix                                                                                                                                           |
| ---------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Slash commands not appearing | Not synced or wrong application ID | Wait up to an hour, re‑invite with correct scopes, or try force closing and restarting discord (HTOP or task manager). Check `on_ready` logs. |
| COD not sending              | Time format invalid                | Use 24h `HH:MM`, verify it was accepted (ephemeral confirmation).                                                                             |
| Multiple messages per day    | Duplicate tasks before restart     | Using `start_cod` cancels existing task for a channel — ensure you're not launching multiple bot instances.                                   |
| Empty coaster fields         | RCDB layout change                 | Inspect homepage HTML and adjust parser logic.                                                                                                |

## Security & Rate Considerations

Currently, all scraping is on-demand or once per day. Heavy usage of `/rcdblist` with a large amount could stress RCDB; consider capping `amount` or adding short sleeps.

## License
https://raw.githubusercontent.com/sqnder0/rcdb/refs/heads/master/LICENSE

---

Happy riding! 🎢
