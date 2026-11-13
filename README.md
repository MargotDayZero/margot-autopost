# Margot Autopost

Posts one Instagram carousel for @margotdayzero every day, automatically.

| When (Eastern) | What happens | Your part |
|---|---|---|
| ~6 PM the night before | Claude writes tomorrow's carousel in Margot's voice, slides are rendered, and GitHub opens an issue **"Post for YYYY-MM-DD"** with previews. | Nothing. Glance at it if you like. |
| 8 AM | If that issue is still open, the carousel is posted with Instagram's AI label on, and the issue closes with a link. | Nothing. |
| To skip a day | Close that day's issue before 8 AM. | One tap. |
| Mondays | An expiring ("IG") token is refreshed. Tokens that start with "EA" never expire and are left alone. | Nothing. |

Times shift one hour later during daylight saving time.

## Content rules (edit `SYSTEM` and `PILLARS` in `scripts/generate.py`)
- Weekday pillars: Mon Three Numbers, Tue Keep, Wed Cut, Thu Earn, Fri Build, Sat Starting Over, Sun Monthly Twenty.
- General education only. No personalized advice, no invented statistics, no income or results claims.
- No AI wording on slides or captions. No invented personal history. No em dashes.
- Every caption ends with the sign-off "Day one counts.", points to the link in bio (free Three Numbers Starter Sheet, or on Fri and Sun the $17 Day Zero Workbook), and has the line "General education, not financial advice."
- A draft that breaks a rule is rejected and Claude rewrites it (3 tries). If all fail, nothing is drafted and the next day's run starts fresh.

## Secrets (Settings, Secrets and variables, Actions)
| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (the account needs prepaid credit) |
| `IG_USER_ID` | Margot's Instagram user ID |
| `IG_ACCESS_TOKEN` | Margot's token from the Meta app (never pasted into chat) |
| `GH_SECRETS_TOKEN` | Only if the token starts with `IG`: a fine-grained token for this repo with Secrets read/write |

Also: Settings, Actions, General, Workflow permissions, **Read and write permissions**.
The repo must stay **public** so Instagram can fetch the images.

## Test
Actions, **Draft tomorrow's post**, Run workflow. Review the issue. To post right away:
Actions, **Publish today's post**, enter that draft's date.

## Controls
Skip a day: close the issue. Pause: disable the workflows. Edit a caption before it posts:
edit `drafts/<date>/post.json`.

## Threads (text-only daily tip)
Separate from the Instagram flow above, same approval idea. Never touches the Instagram token.

| When (Eastern) | What happens | Your part |
|---|---|---|
| ~6:30 PM the night before | Claude writes tomorrow's text-only tip (450 characters or fewer, ends with "Day one counts."). GitHub opens an issue **"Threads for YYYY-MM-DD"** with the exact text. | Nothing. |
| ~11 AM (noon in daylight time) | If that issue is still open, the tip is posted to Threads and the issue closes with a link. | Nothing. |
| To skip a day | Close that day's issue before it posts. | One tap. |
| Mondays | The 60-day Threads token is refreshed and stored. | Nothing. |

Goal: sell the workbook and grow a following. Mon and Sun tips point to the free Starter Sheet, Wed and Fri to one specific part of the $17 workbook (link in bio). Tue, Thu and Sat are pure value written for replies, saves and shares. A reviewed 28-post library is in `content/threads_library.json`.
Same content rules as the carousel (`BANNED`, no income claims, no invented history). Edit `SYSTEM` and `FORMATS` in `scripts/threads_generate.py`.

Extra secrets: `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN` (long-lived Threads token, never pasted into chat), `GH_SECRETS_TOKEN` (fine-grained token for this repo with Secrets read/write, needed for the weekly refresh).
Workflows: `threads-draft.yml`, `threads-publish.yml`, `threads-refresh-token.yml`. Test: Actions, **Threads - draft tomorrow's tip**, Run workflow.
