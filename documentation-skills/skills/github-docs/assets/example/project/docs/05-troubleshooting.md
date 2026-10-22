# Chapter 5: Troubleshooting

This chapter lists common problems with their fixes, then how to get help.

## 5.1 Common problems

<!-- index: troubleshooting; logs -->

| Problem | Likely cause | Fix |
|---|---|---|
| The sign-in page doesn't load | You opened `0.0.0.0` or `localhost` from another device | Open `http://<server-ip>:8484` |
| Unraid says the port is in use | Another app uses `8484` | In the template, change the host side of **Web UI port** to a free port, such as `8485` |
| Settings are gone after an update | **Appdata path** wasn't mapped | Map it as in Chapter 2, then restore your backup into it |
| Devices don't find each other | Peer port blocked or [DHT](glossary.md#dht) off | Turn on **Peer discovery (DHT)** and allow `6990` [UDP](glossary.md#udp) in your firewall |
| Beacon is slow on Windows | Real-time scanning checks every database write | Add `C:\ProgramData\Beacon` as a Defender exclusion |

## 5.2 Get help

Ask on the project's **Issues** page on GitHub. Include your Beacon version, install method, what you expected and what happened.

To copy the last lines of the log on Unraid:

1. Open the Unraid terminal from the **>_** icon at the top right of the web interface.
2. Run the command below and copy its output.

   In the Unraid terminal, paste:

   ```bash
   docker logs beacon --tail 50
   ```

   **Result:** The last 50 log lines appear. Replace the API key with `<redacted>` and public IP addresses with `x.x.x.x` before posting.

<!-- nav:start -->
---

[← Chapter 4: Keep Beacon safe](04-keep-beacon-safe.md) · [Contents](README.md#contents) · [Appendix A: Answers to check your understanding →](appendix-a-answers.md)
<!-- nav:end -->
