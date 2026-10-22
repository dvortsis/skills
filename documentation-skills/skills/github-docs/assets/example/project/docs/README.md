# Beacon setup guide

Install Beacon, set it up safely and keep it running without losing your files.

## Who this guide is for

You can install an app from your NAS app catalog or run a Windows installer. You can open a web page by its address and paste a command when told where. This guide explains each setup choice and gives the safe answer.

## How to use this guide

Read the chapters in order the first time. Later, use the table below to jump to a task.

### Where to find each task

| If you want to | Go to |
|---|---|
| Choose between Unraid, Docker Compose and Windows | [Chapter 1](01-before-you-start.md) |
| Install Beacon and keep its data through updates | [Chapter 2](02-install-beacon.md) |
| Sign in and set the network options | [Chapter 3](03-set-up-beacon.md) |
| Keep Beacon off the internet and back it up | [Chapter 4](04-keep-beacon-safe.md) |
| Fix a problem or ask for help | [Chapter 5](05-troubleshooting.md) |

## Contents

<!-- contents:start -->
- [Chapter 1: Before you start](01-before-you-start.md)
  - [1.1 Choose an install method](01-before-you-start.md#11-choose-an-install-method)
  - [1.2 Keep your files through updates](01-before-you-start.md#12-keep-your-files-through-updates)
  - [1.3 Check your understanding](01-before-you-start.md#13-check-your-understanding)
- [Chapter 2: Install Beacon](02-install-beacon.md)
  - [2.1 Install on Unraid](02-install-beacon.md#21-install-on-unraid)
  - [2.2 Template fields](02-install-beacon.md#22-template-fields)
  - [2.3 Install with Docker Compose](02-install-beacon.md#23-install-with-docker-compose)
  - [2.4 Install on Windows](02-install-beacon.md#24-install-on-windows)
  - [2.5 Check your understanding](02-install-beacon.md#25-check-your-understanding)
- [Chapter 3: Set up Beacon](03-set-up-beacon.md)
  - [3.1 Sign in for the first time](03-set-up-beacon.md#31-sign-in-for-the-first-time)
  - [3.2 Network settings](03-set-up-beacon.md#32-network-settings)
  - [3.3 Check your understanding](03-set-up-beacon.md#33-check-your-understanding)
- [Chapter 4: Keep Beacon safe](04-keep-beacon-safe.md)
  - [4.1 Reach Beacon away from home](04-keep-beacon-safe.md#41-reach-beacon-away-from-home)
  - [4.2 Protect the API key](04-keep-beacon-safe.md#42-protect-the-api-key)
  - [4.3 Back up and update](04-keep-beacon-safe.md#43-back-up-and-update)
  - [4.4 Check your understanding](04-keep-beacon-safe.md#44-check-your-understanding)
- [Chapter 5: Troubleshooting](05-troubleshooting.md)
  - [5.1 Common problems](05-troubleshooting.md#51-common-problems)
  - [5.2 Get help](05-troubleshooting.md#52-get-help)
- [Appendix A: Answers to check your understanding](appendix-a-answers.md)
- [Appendix B: Settings reference](appendix-b-settings-reference.md)
- [Glossary](glossary.md)
- [Revisions](revisions.md)
- [Index](index.md)
<!-- contents:end -->

## What you need

- A server or PC that stays on: an Unraid server, any computer with Docker, or a Windows 10 or 11 PC.
- About 10 minutes, and access to your server's web interface or an administrator account on the PC.
- A password manager for the Beacon password and API key.

## About this guide

This guide covers Beacon 2.4. Last updated 2026-10-22. Facts come from `unraid/beacon.xml`, `docker-compose.yml` and `installer/beacon.iss` in the Beacon repository.

<!-- nav:start -->
---

[Chapter 1: Before you start →](01-before-you-start.md)
<!-- nav:end -->
