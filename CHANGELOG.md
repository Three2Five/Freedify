# Changelog

All notable changes to Freedify will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

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
