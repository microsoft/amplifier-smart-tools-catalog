---
smart_tool_format: 1
name: spotify
version: 0.1.0
description: >
  Controls Spotify playback (play, pause, skip, volume), searches the catalog,
  browses playlists and devices, and launches the desktop app. Use when the
  task is about music, songs, playlists, Spotify, or playing/pausing/searching
  audio.
use_cases:
  - Answer "what's playing" / "what song is this" and report progress
  - Play a specific track by search query, or resume paused playback
  - Pause, skip, or adjust volume on the active playback device
  - Search Spotify's catalog for tracks by artist, title, or album
  - Browse the user's playlists or list available playback devices
  - Launch the Spotify desktop app when no device is available
platforms:
  - linux
  - macos
requires:
  - name: network access to Spotify's APIs
    purpose: >
      api.spotify.com and accounts.spotify.com must be reachable over HTTPS.
      Without it, no capability can run.
    install: docs/network.md
  - name: Spotify OAuth credentials
    purpose: >
      Every capability needs a Spotify access token, either supplied directly
      or obtained by refreshing a client id/secret/refresh token trio. Without
      either, every capability raises with a remedy.
    install: docs/auth.md
  - name: Spotify Premium
    purpose: >
      Browsing, search, now-playing, playlists, and devices all work on a
      free account. Playback CONTROL (play/pause/next/volume) requires
      Premium; without it, those verbs fail with SpotifyPremiumRequired and a
      remedy pointing at spotify.com/premium.
    install: docs/auth.md
    optional: true
---

# spotify

Spotify playback control, catalog search, and diagnostics. One library, one
thin `spotify` CLI.

## Sharp edges

- **Playback control needs Premium.** `play`, `pause`, `next`, and `volume`
  all raise `SpotifyPremiumRequired` on a free account. `now-playing`,
  `search`, `playlists`, and `devices` work regardless.
- **Restricted devices (Sonos, some smart speakers) fall back to the local
  desktop app on macOS only.** When the Web API returns a 403 for a
  restricted device, this tool retries via AppleScript against the local
  Spotify.app. On Linux there is no local fallback -- the original error
  surfaces with a remedy to open Spotify on the computer.
- **`launch` polls for up to 16 seconds** (8 attempts, 2s apart) after
  starting the desktop app, waiting for it to register as a playback device.
  `play` calls the same device-ensure logic automatically.
- **No `--confirmed` write fence.** Unlike a tool that sends email or creates
  records, every verb here is trivially reversible -- pausing is undone by
  playing again. Fencing playback would make this tool useless to an agent
  acting on a live request.
- **Every verb is deterministic.** There is no model-backed path in this tool
  -- it's a direct port of a Spotify Web API skill, not something that
  reasons about your music taste.
- **This tool does not run the OAuth authorization flow itself.** It consumes
  credentials already minted elsewhere; see docs/auth.md.
- **Real speakers, real effect.** Playback commands affect whatever device is
  actually active -- a shared Sonos, a phone, a friend's account session if
  misconfigured.

## Worked invocations

```bash
spotify now-playing
spotify play --query "Bohemian Rhapsody"
spotify play
spotify pause
spotify next
spotify search --query "chill jazz" --limit 10
spotify volume --percent 40
spotify playlists --limit 10
spotify devices
spotify launch --timeout-seconds 20
spotify account
spotify doctor
spotify manifest
```
