# Screenshot shot list for Beacon

Capture these screens from a running copy of Beacon 2.4 to replace the stamped illustrations with live screenshots. Replace any API key, password or public IP address with `<redacted>` before saving.

| Figure | File | Chapter | Screen to capture | Redact before saving | Status |
|---|---|---|---|---|---|
| Figure 2.1 | `images/unraid-template-illustration.svg` | [Chapter 2](02-install-beacon.md) | Unraid **Add Container** page for `beacon` showing **Network Type**, **Web UI port**, **Peer port**, **Appdata path**, **Shared files** and **Apply** | API key field if expanded | Illustrated (`unraid/beacon.xml:11-17`) |
| Figure 2.2 | `images/windows-firewall-illustration.svg` | [Chapter 2](02-install-beacon.md) | **Windows Defender Firewall** prompt for Beacon with **Private networks** checked and **Public networks** unchecked | Windows account name if visible | Illustrated (`installer/beacon.iss:14-15`) |
| Figure 3.1 | `images/network-settings-illustration.svg` | [Chapter 3](03-set-up-beacon.md) | Beacon **Settings** > **Network** page showing **Listen address** (`0.0.0.0`), **Peer discovery (DHT)** (`On`) and **Automatic port forwarding (UPnP)** (`Off`) | Public IP address if shown | Illustrated (`docker-compose.yml:6-8`) |

