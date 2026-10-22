# Audience: the capable installer

The default reader for every guide this skill writes. Replace it only when the user names a different audience, and
then write the new profile in this same shape at the top of `docs/README.md`'s "Who this guide is for".

## What they can do
- Find and install an app from an app store or catalog (for example a NAS app catalog such as Unraid Community
  Applications, a Docker template, or a Windows or macOS installer).
- Open a web page by its address.
- Copy and paste a command when the guide says exactly where to paste it.

## What they may not know
- **The setup itself:** what each install or settings field means (paths, ports, data folders, environment
  variables) and why each one matters.
- **How containers work:** a container is thrown away and rebuilt on every update, and only mapped folders survive;
  what port mappings and network modes do; why some storage paths behave differently from others.
- **Operating-system security and limits:** firewall prompts, download and publisher warnings, what a background
  service is, and why real-time antivirus scanning slows a database.
- **Networking basics:** what port forwarding does, TCP versus UDP, what `0.0.0.0` means, what peer-to-peer
  discovery is when the app uses it.
- **Good security practice:** strong passwords, keeping a web UI off the internet, what a VPN does and doesn't hide,
  keeping API keys private, backups and updates.

The guide explains only the items the project actually involves; `references/concepts.md` holds ready explanations.

## What they want
- To get the app working safely.
- To understand enough to make the right choice at each step.
- Not to break anything.

## What follows for the writing
- Every step they take is one they can do from the "can do" list. Anything else gets an exact instruction (where to
  click, where to paste) or an explanation first.
- Every choice they face shows the recommended, safe answer first (CHOICE_RECOMMENDED).
- Every concept from the "may not know" list gets one sentence where it's needed and a link or a collapsed section for
  the rest (BACKGROUND_LONG).
- Nothing assumes they can read logs, edit config files by hand or use a terminal beyond pasting a given command. When
  a fix needs more, the guide says so and gives the exact command and where to run it (COMMAND_WHERE).
