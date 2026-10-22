# Storytelling method (2026)

Use this before any slide exists. The deck is a structured argument. Visuals support it; they don't replace it.

## 1. Frame (three answers before slide 1)
- **Audience**: who decides, and what they already know.
- **Decision**: the one thing you want them to do or believe. It goes in `meta.decision`.
- **Big idea**: one sentence (30 words or fewer) that states your point and what's at stake. It goes in `meta.big_idea`. If you can't write it, you aren't ready to build.
- **3-minute test**: you can say the whole story aloud in three minutes without slides.

## 2. Structure: answer first
- Slide 2 is the **summary**: the answer, two or three proof points and the ask. Leaders read slide 2 and may stop there.
- Body: **situation → complication → resolution**, or **what → so what → now what** for status updates. Each section proves one proof point from the summary.
- End on the **ask**: decision, owner and date (`closing`). Never end on "Questions?" or "Thank you".
- Put detail, methods, definitions and assumptions in the **appendix** so the main deck stays short. Pre-answer likely questions there.

## 3. Ghost deck (storyboard before design)
- Write the action titles only, in order, then run `lint_deck.py --story`. Read the titles top to bottom: they must tell the whole story on their own.
- If a title can't be read without the slide, rewrite it. If two titles say the same thing, merge the slides.

## 4. Action titles
- Each title is a full-sentence takeaway of 4–15 words that fits on two lines, written in Proper Case, e.g. "Denials Fell 12% After the Edit Fix". Topic labels such as "Denials overview" don't count.
- The title states the conclusion; the visual is the evidence (the assertion–evidence model).
- Use plain words and concrete numbers. Round them ($4.2M, 12%) and label units.

## 5. One idea per slide
- If a slide needs "and" in its title, split it.
- Keep the body to 40 words or fewer. Detail goes in the speaker notes, which are written so the deck works both presented and read cold (async).
- Use progressive disclosure: build complexity over several simple slides rather than one dense one.

## 6. Hybrid and async ready
- Most decks are read as pre-reads or forwarded without a presenter. The titles, summary and source lines must carry the meaning without a voiceover.
- Every number has a source line. Every chart says what to look at (highlight plus title).

## 7. Accessibility is part of quality
- Contrast is at least 4.5:1 for text, with no meaning carried by color alone (label it too).
- Every visual has alt text. Reading order runs title, then visual, then notes. Body text is at least 14pt (the theme uses 20pt for body text).

## Sources
*Storytelling with Data* (context, decluttering, focusing attention, storyboarding off-screen, the 3-minute story); common executive-presentation practice (answer-first communication, an executive summary with a call to action, an assumptions slide, labelled axes, rounded $ with K/M, visuals over text, main takeaways as titles, anticipated questions in the appendix); WCAG 2.2 contrast guidance; a monochrome chart color standard (one focus color, gray for context).
