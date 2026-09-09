---
smart_tool_format: 1
name: hacker-news
version: 0.1.0
description: >
  Fetches the current Hacker News front page as structured data, and can produce a
  themed digest of those stories using a model. Use when you want what the technical
  community is reading right now, either raw or summarised.
use_cases:
  - Get the current Hacker News top stories as structured data
  - Produce a themed digest of what the front page is about today
  - Check whether a topic is currently being discussed on Hacker News
platforms:
  - linux
  - macos
requires:
  - name: network access to hacker-news.firebaseio.com
    purpose: Source of the story data. Without it, no capability can run.
    install: docs/network.md
  - name: model provider credentials
    purpose: >
      Required only by the model-backed digest capability. Without it, deterministic
      fetching still works and digest fails with a remedy.
    optional: true
    install: docs/providers.md
---

# Hacker News

Reach for this when you want to know what the technical community is reading
right now.

`get_top_news` is deterministic and needs no credentials. It returns the front
page as structured stories -- id, title, url, score, author, comment count.

`digest` is model-backed. Hand it stories and an optional focus, and it groups
them into themes with a one-line reason each. It returns structured items, not
a paragraph. Without a provider key it fails and names the remedy; it never
returns a lesser deterministic answer in place of the one you asked for.

## Sharp edges

- The Hacker News API has no key and no documented rate limit, but the front
  page requires one request per story. `limit` is clamped to 50.
- Story `url` is absent for text-only "Ask HN" posts. `hn_url` is always
  present.
- `digest` costs tokens. Fetch once and digest the same result rather than
  re-fetching per digest.

## Worked invocations

```bash
hacker-news get-top-news --limit 10
hacker-news digest --focus "AI infrastructure" --limit 20
hacker-news manifest
```
