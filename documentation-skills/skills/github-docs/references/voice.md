# Voice: calm, matter-of-fact, brief

Say what to do, give the reason in one sentence, and say what's safe. Don't lecture, reassure or pad.

## The three-part pattern
Every instruction, setting and choice follows it:

1. **Do:** the action, verb first, UI labels in bold exactly as they appear.
2. **Why:** one sentence.
3. **Safe:** the recommended value, or what to avoid and what to do instead.

> Set **Appdata path** to `/mnt/user/appdata/<app>`. The app keeps its database and settings there, and it's the one
> folder that survives an update. Keep the default unless you already store appdata somewhere else.

## Choices
Show the recommended option first, marked `(recommended)`, with when to pick the others. Name an unsafe option
plainly, say why in one sentence, and give the safe alternative in the same place (UNSAFE_ALTERNATIVE).

| Option | When to use it |
|---|---|
| **Bridge (recommended)** | Works for almost everyone. Only the ports you map are reachable. |
| Host | Only when the app's docs say it needs it. Every port the app opens is reachable on your network. |

> [!WARNING]
> Don't forward the web UI port on your router. That puts the login page on the internet. To reach the app away
> from home, use a VPN such as WireGuard or Tailscale instead.

## Words and sentences
- Second person, present tense, active voice: "Select **Save**", not "The Save button should be selected".
- Sentences of 25 words or fewer (SENTENCE_LONG warns). One idea per sentence.
- One name per thing, matching the app's own labels (TERM_CONSISTENT in spirit; the glossary holds the names).
- Define a term the first time a page uses it, or link it to the glossary (GLOSSARY_LINK).
- Numbers and values in code format: `8080`, `/mnt/user/appdata`, `0.0.0.0`.

## Don't
- **Reassure:** "Don't worry", "Rest assured", "It's easy", "Nothing can go wrong". State the safe fact instead:
  "Changing this later doesn't lose data."
- **Pad:** "Please note", "It's important to note that", "In order to", "Basically", "Simply", "Of course",
  "Obviously", "Feel free to", "Needless to say" (VOICE_PADDING fails these; "just", "easy" and "very" warn).
- **Lecture:** no history of a technology, no "best practice" sermons. The reason is one sentence; more goes in a
  collapsed section or the concept page.
- **Hedge without a fix:** "This may cause problems" is useless; say which problem and what to do.
- **Blame:** "If you set it wrong" becomes "If the page doesn't load".

## Longer background
Put anything longer than about 70 words that the reader doesn't need to finish the step in a collapsed section, or
link to the concept page:

```markdown
<details>
<summary>Why only mapped folders survive an update</summary>

An update deletes the container and creates a new one from the new image. Files written inside the container go with
it. Files in a mapped folder live on your disk, so the new container sees them again.

</details>
```

Leave a blank line after `<summary>` and before `</details>` so GitHub renders the Markdown inside.
