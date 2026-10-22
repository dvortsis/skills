# Developer Commands (lasting format changes)

Only the developer or agent owner changes format types for everyone. Everyone else uses per-request plan flags.
Every command validates the merged catalog first (CATALOG_SCHEMA) and refuses a change that breaks it; saved changes
print CATALOG_CHANGE and are logged in the overlay with the command line. The base catalog never changes.

| The developer says | Command |
|---|---|
| "Add a huddle card format like the quick reference card" | `catalog_tool.py add huddle-card --family reference-sheet --label "Huddle Card" --like quick-reference-card --alias "shift huddle card"` |
| "Job aids can run two pages" | `catalog_tool.py set job-aid pages=2 words=500` |
| "Add a Safety Note section after When to Use" | `catalog_tool.py section job-aid add "Safety Note" --after "When to Use"` |
| "Make Key Terms required" / "optional" | `catalog_tool.py section quick-reference-card require "Key Terms"` |
| "Put Tips and Get Help side by side" | `catalog_tool.py section quick-reference-card half "Tips"` |
| "Allow up to 7 steps in a Quick Start" | `catalog_tool.py section quick-start limit "Steps" steps=3-7` |
| "Call it a Starter Sheet from now on" | `catalog_tool.py rename quick-start --label "Starter Sheet"` (old name is then flagged as RENAMED_TERM) |
| "We don't do FAQ sheets anymore; use one-pagers" | `catalog_tool.py retire faq-sheet --replaced-by one-pager` |
| "Status reports should be Word documents, not one-pagers" | `catalog_tool.py set status-report renderer=doc-long` |
| "Add a family for posters" | `catalog_tool.py family posters add --label "Posters" --renderer doc-sheet --keywords "poster,banner"` |
| "Undo my changes to job aids" | `catalog_tool.py reset job-aid` |
| "What have we changed?" | `catalog_tool.py diff` |

Persistence: skill files are read-only once installed and the sandbox resets between chats. After a change, deliver
`assets/catalog/overlay.json` and tell the developer to repackage the skill with it (or attach it to a chat and pass
`--overlay`). Agents that share one installed skill share its overlay. One versioned shared copy: the overlay shipped in this skill (mastered in the suite bundle) is the only source for every agent that installs it; `catalog_tool.py drift` (OVERLAY_DRIFT, FAIL) compares a working overlay with it and names both versions (log entries, last date, sha) so the owner knows to repackage.
