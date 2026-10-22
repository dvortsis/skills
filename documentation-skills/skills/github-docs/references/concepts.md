# Concepts the reader may not know

Ready explanations for the topics in `audience.md`. Use only the ones the project involves: discover.py's CONCEPTS line lists them by the id at the end of each
heading. Each entry gives the **one sentence** for the step, the **safe default**, and **background** for a
`<details>` section or the glossary. Adapt names and paths to the project; never copy a value the project doesn't
use. Platform tags: [Docker] [Unraid] [Windows] [Network] [Security].

## Containers

### A container is rebuilt on every update [Docker] `container-rebuilt`
- **One sentence:** An update deletes the container and creates a new one, so only folders mapped to your disk keep
  their files.
- **Safe default:** Map every folder the app writes to (settings, database, downloads) before the first start.
- **Background:** An image is the app's packaged files; a container is one running copy of it. Updating pulls a new
  image and recreates the container from it. Anything written inside the container but outside a mapped folder is
  lost. A mapped folder (a volume or bind mount) lives on the host's disk, so the new container sees the same files.

### Path mappings [Docker] [Unraid] `path-mappings`
- **One sentence:** A path mapping connects a folder on your server (host path) to a folder the app sees (container
  path); change only the host side.
- **Safe default:** Keep the container path from the template or the app's docs; point the host path at a share you
  back up.
- **Background:** In `docker run -v /mnt/user/appdata/app:/config`, the left side is the host and the right side is
  the container. The app is built to read the container path, so changing it breaks the app. Unraid templates show
  them as **Host Path** and **Container Path**.

### The appdata folder [Unraid] [Docker] `appdata`
- **One sentence:** The appdata folder holds the app's settings and database, and it's the folder to back up.
- **Safe default:** `/mnt/user/appdata/<app>` on Unraid; a dedicated folder such as `./data` beside a compose file
  elsewhere.
- **Background:** Unraid's convention is one appdata share with a folder per app. Keep the appdata share on a fast
  pool (usually the cache) so databases don't wait on the array.

### Port mappings [Docker] [Network] `port-mappings`
- **One sentence:** A port mapping makes the app reachable on your server's address at the host port you choose; it
  doesn't open anything to the internet by itself.
- **Safe default:** Keep the template's port; if it's taken, change the host side only.
- **Background:** `-p 8484:8484` maps host port 8484 to the container's port 8484. Two apps can't share a host port.
  `-p 127.0.0.1:8484:8484` limits it to the server itself. Reaching it from the internet needs a router port
  forward, which the guide should tell the reader not to add for a web UI.

### Network modes [Docker] [Unraid] `network-modes`
- **One sentence:** Bridge mode keeps the app on a private network and reaches it only through the ports you map.
- **Safe default:** Bridge. Use host mode only when the app's docs require it.
- **Unsafe:** Host mode makes every port the app opens reachable on your network; a custom network with its own IP
  (Unraid `br0`, macvlan or ipvlan) gives the container its own address, which the reader then has to find and
  protect. Use bridge with mapped ports instead unless the app needs its own address.
- **Background:** In host mode, port mappings are ignored and the app listens directly on the server's interfaces.
  With macvlan, the container usually can't reach the host itself by default.

### `/mnt/user` versus `/mnt/cache` [Unraid] `mnt-user-cache`
- **One sentence:** `/mnt/user/...` is the share as a whole across disks and pools; `/mnt/cache/...` (or
  `/mnt/<pool>/...`) is the same files on one pool only.
- **Safe default:** Use `/mnt/user/appdata/<app>` with the appdata share kept on the cache pool. Use a direct pool
  path only when the app's docs recommend it for database speed.
- **Caution:** Never copy or move files between a `/mnt/user/<share>` path and a `/mnt/disk*` or `/mnt/<pool>` path
  of the same share; the source and destination can be the same file, and the copy can destroy it. Copy within one
  kind of path.
- **Background:** User share paths go through Unraid's share layer, which adds overhead that databases notice. On
  Unraid 6.12 and later, a share that lives entirely on one pool (an exclusive share) skips that layer.

### File ownership (PUID and PGID) [Docker] [Unraid] `puid-pgid`
- **One sentence:** PUID and PGID set which user owns the files the app writes, so you can open and back them up.
- **Safe default:** `99` and `100` on Unraid (nobody:users); on other Linux hosts, your own IDs from `id`.

## Windows

### Firewall prompts [Windows] `firewall`
- **One sentence:** Windows asks whether the app may accept connections; allow it on private networks only.
- **Safe default:** Check **Private networks**; leave **Public networks** unchecked.
- **Background:** Private is your home network; public is a café or airport network. Allowing public networks lets
  anyone on that network reach the app.

### SmartScreen and download warnings [Windows] `smartscreen`
- **One sentence:** "Windows protected your PC" appears for apps Windows hasn't seen often, not only for harmful ones.
- **Safe default:** Download only from the project's official release page. Select **More info**, check the
  publisher name matches, then **Run anyway**.
- **Unsafe:** Running an installer from a mirror, forum post or re-upload. Get it from the official release page
  instead.

### Microsoft Defender warnings [Windows] `defender`
- **One sentence:** Don't turn Defender off to install an app; if it blocks a file you downloaded from the official
  page, check the file and report a false positive.
- **Safe default:** Compare the file's checksum with the one on the release page (`Get-FileHash <file>` in
  PowerShell), then restore it from **Protection history** only if they match.

### Background services [Windows] `services`
- **One sentence:** A service runs the app in the background, starts with Windows and keeps running when you sign
  out.
- **Safe default:** Let the installer create it; manage it in **Services** (press **Win+R**, type `services.msc`).

### Real-time scanning slows a database [Windows] `realtime-scan`
- **One sentence:** Defender scans every file the app writes, and a database writes constantly, so exclude only the
  app's data folder.
- **Safe default:** In **Windows Security** > **Virus & threat protection** > **Manage settings** > **Exclusions**,
  add the app's data folder.
- **Unsafe:** Excluding a downloads folder, a whole drive or the app's install folder. Exclude only the data folder.

### Administrator prompts (UAC) [Windows] `uac`
- **One sentence:** The installer asks for administrator rights to install the service; approve it only when you
  started the installer yourself.

## Networking

### IP addresses and `localhost` [Network] `ip-localhost`
- **One sentence:** Open the app at your server's local address, such as `http://192.168.1.20:8484`; `localhost`
  works only on the same machine.

### What `0.0.0.0` means [Network] `zero-address`
- **One sentence:** As a listen address, `0.0.0.0` means "every network on this machine"; it isn't an address you
  type into a browser.
- **Safe default:** Inside a container it's normal and required. On a PC where you only use the app locally, prefer
  `127.0.0.1`, which only that PC can reach.

### TCP and UDP [Network] `tcp-udp`
- **One sentence:** Most traffic uses TCP; peer discovery, voice and some VPNs use UDP, and firewall and port-forward
  rules are set per protocol.
- **Safe default:** Open or forward exactly the protocols the app's docs list for that port, often both TCP and UDP
  for a peer port.

### Port forwarding [Network] [Security] `port-forwarding`
- **One sentence:** A port forward sends traffic from the internet to one device on your network.
- **Safe default:** Forward only the port the app documents for incoming peer connections, if it needs one.
- **Unsafe:** Forwarding the web UI port, or using the router's DMZ setting. Use a VPN for remote access instead.

### UPnP and NAT-PMP [Network] [Security] `upnp`
- **One sentence:** UPnP lets an app open router ports by itself, without you reviewing them.
- **Safe default:** Off in the app; add the one port forward you need by hand.

### DHT and peer discovery [Network] `dht`
- **One sentence:** The DHT lets the app find peers without a central server; it uses UDP and shares your public IP
  address with other peers.
- **Safe default:** Leave it as the app ships it; if your IP must stay private, route the app through a VPN.

## Security

### Strong passwords [Security] `strong-passwords`
- **One sentence:** Use a long, unique password for the web UI, kept in a password manager.
- **Safe default:** At least 16 characters or four random words; change any default password before first use.

### Keep the web UI off the internet [Security] `web-ui-offline`
- **One sentence:** The web UI is for your home network; reaching it from outside should go through a VPN.
- **Safe default:** No port forward for the web UI. For remote access, use a self-hosted VPN such as WireGuard or a
  mesh VPN such as Tailscale.

### What a VPN does and doesn't hide [Security] `vpn`
- **One sentence:** A VPN hides your IP address from the sites and peers you connect to and hides your traffic from
  your internet provider, but the VPN provider can see it.
- **It doesn't:** make an exposed web UI safe, protect against malware, hide what you do inside accounts you sign in
  to, or keep traffic private if the app connects outside the VPN.
- **Safe default:** When the app must only use the VPN, bind it to the VPN interface or run it in a container that
  routes through the VPN, and check its reported IP.

### API keys [Security] `api-keys`
- **One sentence:** An API key is a password for software; anyone who has it can act as you.
- **Safe default:** Copy it only into the field that needs it; mask it in screenshots and logs; regenerate it if it
  ever appears in public.

### Backups [Security] `backups`
- **One sentence:** Back up the app's data folder on a schedule, keep one copy off the server, and test a restore.
- **Safe default:** Stop the app (or use a backup tool that stops it) so the database copy is complete.

### Updates [Security] `updates`
- **One sentence:** Updates fix security problems; read the release notes and back up before a major version.
- **Safe default:** Update through the same place you installed from (the app catalog, the installer or the compose
  file).

### Sharing logs for help [Security] `sharing-logs`
- **One sentence:** Logs can contain keys, addresses and file names; remove them before posting.
- **Safe default:** Replace keys with `<redacted>` and public IP addresses with `x.x.x.x`.
