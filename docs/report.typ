#set text(font: "Roboto", size: 12pt)
#set heading(numbering: "1.1")

#align(center, text(size: 9mm, [Software Engineering Project 3]))
#align(center, text(size: 1cm, [UUUTorrent]))
#figure(image("logo.png", width: 50%),)
#align(center, text(size: 0.8cm, [Technical Report]))
#line(start: (-10%, 0%), end: (110%, 0%))
#align(center, text(size: 9mm, [BEST SE TEAM EVER \ (UNNAMED UNARMED UNTAMED)]))
#align(center, text(size: 6mm, [Sambu Aneesh],))
#align(center, text(size: 6mm, [Vidhi Rathore]))
#align(center, text(size: 6mm, [Bassam Adnan]))
#align(center, text(size: 6mm, [Moida Praneeth Jain]))
#align(center, text(size: 6mm, [Aadi Deshmukh]))



#set page(
  header: [BEST SE TEAM EVER (UNNAMED UNARMED UNTAMED) #h(1fr) Software Engineering #line(start: (-10%, 0%), end: (110%, 0%))], footer: [#line(start: (-10%, 0%), end: (110%, 0%))
    Project 3 Technical Report
    #h(1fr)
    #context counter(page).display("1 of 1", both: true)
    ], margin: (x: 1.5cm),
)

#outline()

#pagebreak()

= Requirements and Subsystems

== Requirements

=== Functional Requirements (FR)

- *FR1: Remote Torrent Download & Transfer:* Utilize an Oracle Cloud compute instance with qBittorrent for downloading torrents. Provide authenticated users a mechanism (via TUI) to initiate downloads and securely transfer completed files (e.g., via user-initiated SFTP/SCP) to local devices.

- *FR2: User and Access Management:* Implement user authentication (login/password) and authorization. Define distinct roles: 'User' (manages personal downloads, feeds, watchlist) and 'Admin' (manages users, system monitoring access).

- *FR3: RSS Feed Management & Automation:* Allow users to add, view, remove, and define filter criteria (keywords, regex) for RSS feeds. The system backend must periodically check feeds, match against filters, and auto-initiate downloads for new items via qBittorrent.

- *FR4: Watchlist Integration & Automation:* Allow users (via TUI) to manage a watchlist (add/remove shows). The backend must integrate with external services (e.g., Anilist API) to fetch watchlist details and identify new episodes/content based on user entries, triggering downloads (potentially correlated with RSS feeds).

- *FR5: Torrent Lifecycle Management:* Enable users (via TUI) to view download status (downloading, seeding, completed, error), pause, resume, and delete their torrents managed by the system.

- *FR6: Admin Monitoring View:* Provide administrators access to a web-based dashboard (Grafana) displaying real-time server resource usage (CPU, RAM, disk, network), qBittorrent statistics, database health, and potentially aggregated user activity/stats.

- *FR7: User Interface (TUI):* Provide a cross-platform Terminal User Interface (Textual) for user interaction: displaying status, adding torrents/feeds, managing the watchlist, and getting information for file transfers. Runs on the user's machine.

=== Non-functional Requirements (NFR)

- *NF1: Performance (RSS Processing):* Check each RSS feed at least every 10 minutes. Processing time per feed check (filtering, download initiation) < 30 seconds under normal load.

- *NF2: Performance (Concurrency):* Support at least 50 concurrent torrent downloads/seeds without significant API/TUI responsiveness degradation. (Network throughput depends on OCI/peers).

- *NF3: Reliability (Backup & Recovery):* Perform automated daily database backups (PostgreSQL). RTO: 1 hour. RPO: 24 hours.

- *NF4: Security (Authentication):* Secure user authentication (hashed+salted passwords). Protect API endpoints with token-based authentication (e.g., JWT).

- *NF5: Security (Authorization):* Enforce authorization rules: users manage only their own resources; admins have specific elevated privileges (user management, monitoring access).

- *NF6: Usability (TUI):* The TUI should be intuitive for terminal users, providing clear feedback and navigation.

- *NF7: Resource Constraints (OCI):* Operate within OCI Always Free tier limits (Ampere A1 CPU/RAM, storage, network egress). Monitor usage.

- *NF8: Maintainability:* Ensure modular, documented backend code with tests for easier updates.

- *NF9: Monitoring Availability & Freshness:* The Admin monitoring view (Grafana) should be highly available (best effort on free tier) and display metrics with a latency of <= 1 minute from collection time.

=== Architecturally Significant Requirements

The following requirements have the most significant impact on the architectural design:
- *NF1 & NF2 (Performance):* Drive choices for async backend, database tuning, OCI instance sizing.
- *NF3 (Reliability):* Dictates backup strategy and operational procedures.
- *NF4 & NF5 (Security):* Fundamental; require secure design of API, auth flows, and data storage.
- *NF6 & FR7 (Usability/TUI):* Drive the choice of Textual and interaction design.
- *NF7 (Resource Constraints):* A primary constraint influencing technology choices and scale.
- *FR6 & NF9 (Monitoring):* Dictates the monitoring stack (Prometheus/Grafana) and its configuration.
- *FR4 (Watchlist Integration):* Requires careful design of backend interaction with external APIs.
