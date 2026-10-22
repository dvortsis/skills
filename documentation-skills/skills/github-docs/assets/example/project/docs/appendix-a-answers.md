# Appendix A: Answers to check your understanding

Answers to the questions at the end of each chapter, in the same order.

## Chapter 1: Before you start

1. The Unraid app catalog. Beacon belongs on the device that stays on, and the laptop sleeps.
2. The appdata folder. It's also the folder to back up.

## Chapter 2: Install Beacon

1. The host side. The container side stays `8484` because Beacon is built to listen there.
2. **Private networks** only. Public networks would let strangers on the same network reach Beacon.

## Chapter 3: Set up Beacon

1. `http://<server-ip>:8484`, using your server's address on your home network.
2. Off. Add a port forward by hand only when Chapter 5 says you need one.

## Chapter 4: Keep Beacon safe

1. A VPN to your home network, such as Tailscale or WireGuard.
2. Regenerate the key under **Settings** > **API** and paste the new one into each app that uses it.

<!-- nav:start -->
---

[← Chapter 5: Troubleshooting](05-troubleshooting.md) · [Contents](README.md#contents) · [Appendix B: Settings reference →](appendix-b-settings-reference.md)
<!-- nav:end -->
