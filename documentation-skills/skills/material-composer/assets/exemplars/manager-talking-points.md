---
format: manager-talking-points
title: UAT Page Talking Points for Team Leads
audience: Partner team leads
owner: BI / Analytics
sources:
  - UAT process reference (synthetic example content); example dates
---

## Key Message
Your testers now use the user acceptance testing (UAT) page to check each dashboard against their own reports before it goes live.

## Why This Is Changing
Every test scenario traces to a business question and is checked against your team's own source of truth. The team writes the scenarios; your testers supply the real-world values.

## What Changes for Your Team
- Testers enter values on **1 · Parameters**, record results on **2 · Testing** and sign off on **3 · Sign-off**.
- Testers bring the legacy report or extract. Nobody estimates a value from memory.
- Each Fail or Blocked result opens an issue in **Issues found** for the business intelligence (BI) team to review.

## Anticipated Questions
### Why Can't a Tester Record a Result?
**Record result** stays disabled until every value for the scenario is entered.

### What Happens After a Fail or Blocked Result?
The tester picks a severity (how much it matters) and adds a note, which opens an issue in **Issues found**. The BI team marks it FIX REQUIRED, NOT A DEFECT or DEFERRED TO PHASE 2, with the reason.

### Can a Tester Change a Value After Entering It?
Yes. **Reopen to update** changes a completed card and keeps its history.

### What if Tests Have Not Passed at Sign-off?
The **3 · Sign-off** tab warns when tests have not passed or issues are still open.

## What to Ask Your Team to Do
1. Find the legacy report or extract for each dashboard before testing starts.
2. Enter every value on **1 · Parameters** by October 21 (example date).
3. Refresh live values, such as open ticket IDs, when the page flags them.
