# Chapter 1: Before you start

Pick how you'll run Beacon and learn the one rule that keeps your files safe through updates.

> [!NOTE]
> **What you will learn**
> - Choose the install method that fits the device you have.
> - Name the two folders Beacon must keep on your disk.

## 1.1 Choose an install method

<!-- index: install method; Unraid; Windows installer -->

All three methods run the same Beacon. Pick the one that matches the device that stays on.

| Option | When to use it |
|---|---|
| **Unraid app catalog (recommended)** | You have an Unraid server. Updates come from the **Apps** tab. |
| Docker Compose | You run Docker on another Linux machine or a NAS without an app catalog. |
| Windows installer | Beacon runs on a Windows PC that stays on. |

## 1.2 Keep your files through updates

<!-- index: container; data folders -->

On Unraid and Docker, Beacon runs in a [container](glossary.md#container). An update replaces the container, so Beacon keeps only what it stores in folders mapped to your disk.

Beacon uses two folders:

- **Appdata:** settings and the database. Back this one up.
- **Shared files:** the files Beacon shares between your devices.

<details>
<summary>Why files outside a mapped folder disappear</summary>

An update deletes the container and creates a new one from the new version. Files written inside the old container go with it. A mapped folder lives on your server's disk, so the new container sees the same files.

</details>

## 1.3 Check your understanding

1. You have an Unraid server and a Windows laptop that sleeps at night. Which install method fits?
2. Which folder holds Beacon's settings and database?

> [!TIP]
> **Key takeaways**
> - Install Beacon on the device that stays on.
> - Beacon keeps only what's in its two mapped folders.

<!-- nav:start -->
---

[← Beacon setup guide](README.md) · [Contents](README.md#contents) · [Chapter 2: Install Beacon →](02-install-beacon.md)
<!-- nav:end -->
