# House Conventions (borrowed by every format)

Generic conventions for internal reference sheets, job aids, training and change communications. The project's brand
profile (`scripts/brand.py show --source <source>`) decides everything that is brand-specific: logo, colors, fonts, the
footer owner line and the house terms (`terminology` in brand.json). Where the project's own style guide says otherwise,
follow it and name it in the plan's sources.

## Every printed or PDF material
* Footer: the brand footer (for example "©<year> <owner>" from the project's LICENSE or brand.json `footer`) plus title,
  version, revision date and "Page X of Y". The sheet layout, forms and documents add it automatically; with no owner
  known there is no copyright line, never an invented one.
* The project logo where the layout has one; with no logo, none is drawn.
* A one-line purpose near the top ("Use this when ...", "Purpose: ...").
* A help block last: "Get Help" or "Questions?" naming a channel or role (support ticket, team mailbox, review lead),
  never a private person.
* Version and revision date visible; origination date for policies and procedures.
* Proper Case for titles and headings; the word after a hyphen stays lowercase ("Sign-off") unless it is a name the
  brand profile lists.
* The brand body font for text; headings in the brand primary color, bands in the brand dark color; the alert color only
  for a warning, miss or failed step. Every text color pair passes WCAG AA (brand.py adjusts and reports any change).

## Words
* Second person, imperative steps that start with a verb; one action per step.
* Screen labels exactly as the screen shows them, in bold.
* Define a term at first use for non-developer audiences; no internal team or tool names for partners.
* No hype, filler or generic openers. Open with the change, the task or the ask.
* House terms (product names, preferred words) come from the project's terminology file; the shared AP rules apply always.

## Change and communication
* Plan kits with ADKAR stages (awareness, desire, knowledge, ability, reinforcement).
* Before rollout every message states why it is changing, what changes for the reader ("What's In It For Me") and what to
  do, with dates and where to get help.
* Leaders get talking points before their teams get the announcement.

## Training
* Objectives start with an observable verb; every check has an answer; practice uses realistic but synthetic cases.
* E-learning ships as a self-contained HTML module plus a storyboard; `build_module.py --scorm` adds a SCORM 1.2 zip that
  reports completion and the quiz score. People upload it to their LMS's test or pilot area first, then production; the
  agent cannot upload.
