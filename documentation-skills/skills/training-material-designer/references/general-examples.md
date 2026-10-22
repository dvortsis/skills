# General Examples (Any Domain)

Training for an audience that spans domains (all partners, every team in a rollout) draws its examples from this list, or from the one subdomain the request names. Domain-only nouns (accounts, claims, payers, holds, queues, huddles, recon rates, month-end close, metric codes such as K3) confuse readers from other domains. Privacy rules ("never type an account number") are allowed.

| Approved Example | Use It For | Replaces |
|---|---|---|
| A weekly team meeting | Where a report or dashboard is discussed | "the Monday huddle" |
| A monthly review with leaders | Reporting results upward | "the month-end close" |
| Checking whether a goal was met this month | Reading a headline number against its goal | "K3 Recon Rate" |
| Comparing this month with last month | Trends and change arrows | "open accounts this week" |
| Explaining a change to a manager | Notes, drivers and comments | "claim-level work" |
| A list of items your team follows up on each day | The standard workflow example (a list, not a dashboard) | "accounts to work", "Holds" |

Rules: one example idea per passage; name no internal teams, reviews or meetings; keep the same example in every deliverable of a set. When an example or term changes, record the retired term and its replacement in `<file_key>.set.json` (`{"retired": [{"term": "huddle", "replacement": "weekly team meeting"}]}`) so the other deliverables can be checked against it. A documentation overlay skill, when attached, checks this across the set.
