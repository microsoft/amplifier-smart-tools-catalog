---
smart_tool_format: 1
name: gmail
version: 0.1.0
description: >
  Reads and sends Gmail, searches and creates Google Contacts, and reads and creates
  Google Calendar events, all as structured data. Use when the task is about email,
  inbox triage, contacts lookup, or calendar/schedule questions for a Google account.
use_cases:
  - Summarize or triage an inbox (list unread, list by sender, list by label)
  - Read one email's full body and reply to it in-thread
  - Send a new email on the user's behalf
  - Look up a contact's email/phone/organization, or create a new contact
  - Answer "what's on my calendar" / "any meetings today" and create new events
platforms:
  - linux
  - macos
requires:
  - name: network access to the Google APIs
    purpose: >
      gmail.googleapis.com, people.googleapis.com, www.googleapis.com, and
      oauth2.googleapis.com must be reachable over HTTPS. Without it, no
      capability can run.
    install: docs/network.md
  - name: Google OAuth credentials
    purpose: >
      Every capability needs a Google OAuth access token, either supplied
      directly or obtained by refreshing a client id/secret/refresh token
      trio. Without either, every capability raises with a remedy.
    install: docs/auth.md
---

# gmail

Gmail, Google Contacts, and Google Calendar as structured data. One library,
one thin `gmail` CLI.

## Sharp edges

- **Writes need confirmation.** `send_message`, `reply_message`,
  `archive_message`, `create_contact`, and `create_event` all raise
  `ConfirmationRequired` unless called with `confirmed=True` (or `--confirmed`
  on the CLI). The check happens before any network call or credential
  resolution.
- **`list_messages` costs one API call per matched message.** Gmail's list
  endpoint returns only ids; this tool fetches each message's metadata
  separately to build the summary, so it is N+1 requests, not 1.
- **Gmail search operator syntax** applies to `list_messages`'s `query`:
  `from:user@example.com`, `subject:meeting`, `is:unread`, `has:attachment`,
  `after:2026/03/01`, and combinations thereof (e.g.
  `from:boss@work.com is:unread`).
- **`url` is absent on some Calendar payloads.** `html_link` may be `None`
  for events that were not created through the standard flow.
- **Token refresh needs the whole trio.** `GOOGLE_CLIENT_ID`,
  `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN` must ALL be present for
  auto-refresh; a lone `GOOGLE_ACCESS_TOKEN` works but expires and is not
  renewed by this tool.
- **This tool does not run the OAuth authorization flow itself.** It consumes
  credentials already minted elsewhere; see docs/auth.md.

## Worked invocations

```bash
gmail list --folder INBOX --limit 10 --query "is:unread"
gmail read --message-id <MESSAGE_ID>
gmail send --to someone@example.com --subject "Subject line" --body "Hello there" --confirmed
gmail reply --message-id <MESSAGE_ID> --body "Thanks, will do." --confirmed
gmail archive --message-id <MESSAGE_ID> --confirmed
gmail labels
gmail contacts --query "acme.com" --limit 10
gmail contact-create --name "Jane Doe" --email jane@example.com --confirmed
gmail calendar --days 1
gmail calendar-create --summary "Standup" --start 2026-04-15T09:00:00 --end 2026-04-15T09:15:00 --confirmed
gmail me
gmail doctor
gmail manifest
```
