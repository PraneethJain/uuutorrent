# uuutorrent

This project bridges the gap between managing an anime watchlist on Anilist and
downloading episodes via qBittorrent, particularly for those who prefer using
the terminal and self-hosting components remotely.

It addresses a few common scenarios: maybe you're meticulous about media
quality that streaming doesn't always provide, you enjoy terminal-based
interfaces, or you prefer running torrent clients on a separate server rather
than your primary internet connection.

UUUTorrent connects your Anilist watchlist to a qBittorrent instance running on
a remote server (VPS, home server, etc.), all controlled via a Textual TUI on
your local machine.

## The Core Idea

- Run the Textual TUI locally. It fetches and displays your 'Currently
Watching' list from Anilist.

- See an episode you haven't watched? Select it in the TUI to trigger the
download process.

- The self-hosted backend component searches nyaa.si for a suitable torrent
(defaults to 1080p if available).

- It instructs your remote qBittorrent instance to begin the download.

- You can monitor progress, pause, resume, or delete the torrents on your server
directly from the TUI.

- Crucially: Once downloaded on your server, you are responsible for transferring
the files to your local machine using tools like scp, sftp, rsync, Syncthing,
etc. UUUTorrent only manages the download initiation and remote torrent state.

- Also comes with a nice Grafana dashboard!

## Installation

### Prerequisites
- A server (Linux recommended) with SSH access.

- Docker and Docker Compose installed on the server.

- Git installed on both server and local machine.

- Python 3.12+ installed on both server (if not using Docker for backend) and
local machine.

- qBittorrent installed and running on the server, with its Web UI enabled. Note
the IP/Port accessible to the backend, plus the Web UI username and password.

- An Anilist Account.

- A UUUTorrent account (invite only).

### Backend Setup (on the Server)

- Clone the repository and `cd` into the `backend` folder.
- Copy `.env.example` to `.env` and update the variables accordingly.
- run `docker compose up -d`.

### Frontend Setup (on your Local Machine)

- Clone the repository and `cd` into the `frontend` folder.
- Copy `.env.example` to `.env` and update the variables accordingly.
- Install the requirements and run `main.py`.

## Usage Notes
- Navigate the TUI using arrow keys, Enter, or mouse clicks.

- Clicking an anime card expands it to show details and action buttons.

- Remember that downloaded files reside on your server. Transfer them locally
using your preferred method (scp, sftp, rsync, Syncthing, etc.).

## Disclaimer

This is a personal project developed for a specific workflow. It may contain
bugs or have limitations. Use it responsibly and ensure you comply with
copyright laws and the terms of service for Anilist and Nyaa.si. Self-hosting
requires attention to server security and maintenance.

## References

- https://github.com/Textualize/textual
- https://docs.anilist.co/
- https://nyaa.si/
- https://www.oracle.com/in/cloud/compute/

