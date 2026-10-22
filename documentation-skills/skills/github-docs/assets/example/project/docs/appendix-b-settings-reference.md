# Appendix B: Settings reference

Every Beacon setting in one table. The recommended value is the safe choice for most setups.

<!-- index: settings reference -->

| Setting | What it does | Recommended | Notes |
|---|---|---|---|
| Web UI port | Port your browser uses to open Beacon | `8484` | Change the host side only, if the port is taken |
| Peer port | Port other Beacon devices use to reach this one | `6990` UDP | Don't forward it unless Chapter 5 says to |
| Appdata path | Settings and database | `/mnt/user/appdata/beacon` | Back it up; never copy between `/mnt/user` and `/mnt/cache` paths |
| Shared files | Files Beacon shares | `/mnt/user/beacon` | A share of its own |
| Network type | How the container joins your network | Bridge | Host and custom networks aren't needed |
| PUID / PGID | Owner of the files Beacon writes | `99` / `100` on Unraid | Your own IDs from `id` on other Linux machines |
| API key | Lets other apps control Beacon | Created on first start | Treat it like a password; regenerate if shared |
| Listen address | Networks Beacon accepts connections from | `0.0.0.0` in a container | `127.0.0.1` on a Windows PC used only by you |
| Peer discovery (DHT) | Finds your devices without a server | On | Peers see your public IP address |
| Automatic port forwarding (UPnP) | Opens router ports by itself | Off | Add forwards by hand instead |

<!-- nav:start -->
---

[← Appendix A: Answers to check your understanding](appendix-a-answers.md) · [Contents](README.md#contents) · [Glossary →](glossary.md)
<!-- nav:end -->
