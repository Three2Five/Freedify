# Changelog

All notable changes to Freedify will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

---

## [1.1.4] - 2026-01-23

### Added
- **Selective Track Download**: Checkboxes on each track in album/playlist/queue modals to select specific songs to download
- **Select All Toggle**: Quick select/deselect all tracks with selection count display
- **Queue Download**: Added "Download Selected" button to queue controls

---

## [1.1.3] - 2026-01-23

### Fixed
- **Mobile Gapless Playback**: Fixed "false start" bug where tracks would play briefly, pause for 20 seconds, then restart from beginning when screen is off
- **Track Transition Race Condition**: Added `transitionInProgress` lock to prevent double-trigger between gapless switch and ended event handlers

### Changed
- **Mobile Album Modal**: Two-row track layout on mobile - track name on top row, action buttons (star, heart, duration, queue, download) on second row for better readability
- **Star Icon Visibility**: Star button now uses white outline and gold fill when starred, with glow effect
- **Preload Timing**: Replaced setTimeout with requestAnimationFrame for mobile-friendly track preloading

---

## [1.1.2] - 2026-01-22

### Added
- **Jump Back In Dashboard**: Home screen now shows personalized sections for recent albums, artists, library, and playlists
- **My Library (⭐)**: Save tracks with star icon - separate from playlists, syncs with Google Drive
- **Listening History**: Tracks your last 50 played songs, persists across sessions
- **Library View**: Click "See All" on the dashboard to browse your full starred collection

### Changed
- **Google Drive Sync**: Now syncs Library and History alongside playlists
- **Search Cards**: Added star (☆/★) button to quickly save tracks

---

## [1.1.1] - 2026-01-21

### Fixed
- **Download Metadata**: Fixed "Album: test" overwriting actual album tags in playlist downloads via new Strict Mode logic
- **Album Art**: Fixed missing art/metadata by adding automatic MusicBrainz fallback when primary source fails
- **FLAC Duration**: Fixed 00:00 duration/seeking issues in VLC (corrected ffmpeg pipe handling)
- **Stability**: Hardened backend against 404s and empty metadata fields

---

## [1.1.0] - 2026-01-21

### Added
- **Multi-arch Docker**: ARM64 support for Raspberry Pi, Apple Silicon (M1/M2/M3), and ARM servers
- **Termux/Android support**: Run Freedify directly on Android via Termux
- **Termux documentation**: New section in README and deployment guide
- **Cross-platform cache**: Cache now defaults to `~/.freedify_cache` (works on Termux)
- **Apple Music workaround**: Documentation for importing Apple Music playlists via Spotify

### Changed
- **Docker workflow**: Added QEMU emulation for ARM64 builds
- **Cache filenames**: MD5 hash long `LINK:` IDs to prevent filename errors
- **API reliability**: Updated Tidal fallback servers (squid, spotisaver, kinoplus, binimum, qqdl)
- **User-Agent header**: Added custom `Freedify/1.0` User-Agent for API requests

### Fixed
- **iOS audio**: Added silent audio keepalive to prevent screen lock suspension
- **Keyboard shortcuts**: Play/pause now correctly uses Enter key (not Space)
- **Docker Compose**: Updated to use Docker Hub image by default with NAS-friendly options

---

## [1.0.0] - 2026-01-18

### Added
- Initial public release
- Lossless FLAC streaming (16-bit & 24-bit Hi-Res)
- AI Smart Playlists with Gemini
- Multi-source search (Deezer, YouTube Music, Jamendo, Phish.in)
- Google Drive sync for playlists
- ListenBrainz scrobbling
- Docker support with auto-publish to Docker Hub
- Visual deployment guide for Localhost, Railway, and Render

---

*For changes before v1.0, see [commit history](https://github.com/BioHapHazard/Freedify/commits/main).*
