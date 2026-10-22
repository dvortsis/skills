# Chapter 3: Set up Beacon

Sign in for the first time, replace the starting password and set Beacon's network options.

> [!NOTE]
> **What you will learn**
> - Open Beacon from another device on your network.
> - Replace the starting password before anything else.
> - Set each option on the **Network** settings page to its safe value.

## 3.1 Sign in for the first time

<!-- index: sign in; password -->

Open Beacon at your server's address, such as `http://192.168.1.20:8484`. `localhost` works only on the machine running Beacon.

To sign in and replace the starting password:

1. Open `http://<server-ip>:8484` in your browser.
2. Sign in with the user name `admin` and the starting password shown in **Docker** > **beacon** > **Logs**.
3. Select **Settings** > **Account** > **Change password**, and enter a new password from your password manager.
   **Result:** Beacon signs you out. Sign in again with the new password.

`<server-ip>` is your server's address on your home network. Unraid shows it at the top left of its web interface.

> [!IMPORTANT]
> Use at least 16 characters, unique to Beacon. Anyone who reaches the sign-in page can try passwords.

## 3.2 Network settings

<!-- index: Network settings; listen address; UPnP; DHT -->

Open **Settings** > **Network**. Keep the defaults unless a setting below says when to change it.

### Listen address

Which networks on this machine Beacon accepts connections from.

**Recommended:** `0.0.0.0` in a [container](glossary.md#container), which means every network inside it. The [port mapping](glossary.md#port-mapping) decides what reaches it.

**Safe to change later:** Yes. On a Windows PC used only by you, `127.0.0.1` limits Beacon to that PC.

### Peer discovery (DHT)

Lets your Beacon devices find each other without a central server, using [DHT](glossary.md#dht).

**Recommended:** On. Peers see your public IP address, as with any peer-to-peer app.

### Automatic port forwarding (UPnP)

Lets Beacon open ports on your router by itself.

**Recommended:** Off.

**Unsafe:** On, because it opens router ports without asking you. Leave it off and add a forward by hand if Chapter 5 says you need one.

> [!NOTE]
> **Worked example**
> Your phone can't see the server's files while you're both home. Check that **Peer discovery (DHT)** is on, that both devices use the same network, and that the peer port is `6990` [UDP](glossary.md#udp) on both.

## 3.3 Check your understanding

1. You type `http://0.0.0.0:8484` into your browser and nothing loads. What address do you use instead?
2. Should **Automatic port forwarding (UPnP)** be on or off?

> [!TIP]
> **Key takeaways**
> - Replace the starting password before anything else.
> - `0.0.0.0` is a listen address, not an address to open.
> - Keep UPnP off.

<!-- nav:start -->
---

[← Chapter 2: Install Beacon](02-install-beacon.md) · [Contents](README.md#contents) · [Chapter 4: Keep Beacon safe →](04-keep-beacon-safe.md)
<!-- nav:end -->
