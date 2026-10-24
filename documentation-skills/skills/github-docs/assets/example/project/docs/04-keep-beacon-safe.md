# Chapter 4: Keep Beacon safe

Keep Beacon reachable only by you, protect its API key and keep a copy of its data you can restore.

> [!NOTE]
> **What you will learn**
> - Reach Beacon from outside your home without exposing it.
> - Protect and replace the API key.
> - Back up the appdata folder and update without losing settings.

## 4.1 Reach Beacon away from home

<!-- index: remote access; VPN; port forwarding -->

Beacon's sign-in page is for your home network. To use it elsewhere, connect to home through a [VPN](glossary.md#vpn) first.

| Option | When to use it |
|---|---|
| **Tailscale or WireGuard VPN (recommended)** | Any time you use Beacon away from home. |
| No remote access | You only use Beacon at home. |
| Port forward for the web UI | Never. It puts the sign-in page on the internet. |

> [!WARNING]
> Don't add a [port forward](glossary.md#port-forwarding) for `8484` or use your router's DMZ setting. Set up a VPN instead.

<details>
<summary>What a VPN does and doesn't hide</summary>

A VPN you run at home, such as WireGuard or Tailscale, gives your phone a private path to your home network. A commercial VPN does something else. It hides your IP address from the sites and peers you connect to, but the VPN provider can see your traffic. Neither one makes an exposed sign-in page safe.

</details>

## 4.2 Protect the API key

<!-- index: API key -->

The API key lets other apps control Beacon, so treat it like a password. Beacon shows it under **Settings** > **API**.

To replace a key that may have leaked:

1. Open **Settings** > **API** and select **Regenerate key**.
2. Paste the new key into each app that uses it.
   **Result:** The old key stops working right away.

When you share a screenshot or a log, replace the key with `<redacted>`.

## 4.3 Back up and update

<!-- index: backup; updates -->

Back up the appdata folder on a schedule and before each update. An update replaces the [container](glossary.md#container), and the appdata folder is what carries your settings over.

To back up and update on Unraid:

1. On the **Docker** tab, stop `beacon`.
2. Copy `/mnt/user/appdata/beacon` to your backup share with your backup tool, and keep one copy off the server.
3. On the **Docker** tab, select **Check for Updates**, then **Apply Update** next to `beacon`.
   **Result:** Beacon restarts on the new version with your settings.

Read the release notes before a major version, such as 2.x to 3.0.

| Mistake | What to do instead |
|---|---|
| Updating without stopping Beacon first | Stop `beacon` on the **Docker** tab before copying appdata |
| Keeping the only backup on the same server | Keep a second copy on another device or cloud backup |
| Posting a log with the API key still in it | Replace the key with `<redacted>` before sharing |

## 4.4 Check your understanding

1. You want Beacon on your phone at a café. What do you set up?
2. You posted a log that showed your API key. What do you do?

> [!TIP]
> **Key takeaways**
> - Use a VPN for remote access; never forward the web UI port.
> - Regenerate the API key if it was ever shared.
> - Stop Beacon and back up appdata before updating.

<!-- nav:start -->
---

[← Chapter 3: Set up Beacon](03-set-up-beacon.md) · [Contents](README.md#contents) · [Chapter 5: Troubleshooting →](05-troubleshooting.md)
<!-- nav:end -->
