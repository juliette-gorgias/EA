---
name: ama-prep
description: >
  End-to-end Company AMA preparation — syncs Polly questions (with vote counts) from Slack into
  the Notion AMA doc, categorizes and assigns them to execs, posts a heads-up on #exec-internal,
  and checks that every question has an answer. Use this skill whenever the user mentions AMA,
  AMA prep, AMA questions, syncing Polly, prepping the exec AMA, checking AMA answers, or any
  variation of "prep the AMA", "sync the AMA questions", "post AMA to exec", "are AMA answers
  done", or "check AMA readiness". Always use this skill even if the user just says "AMA" or
  "prep the questions" — it covers the full lifecycle from question ingestion to answer verification.
---

# AMA Prep Skill

Automates the Company AMA preparation workflow for Juliette at Gorgias. The AMA is a quarterly
exec Q&A session (usually tied to Virtual Summit, always on a Monday). Employees submit anonymous
questions via the Polly app in #announcements; this skill pulls those questions into the Notion
AMA preparation document, categorizes them, assigns them to execs by topic, notifies the exec
team on Slack, and later verifies that every question has at least one answer bullet.

---

## Key references

| Resource | Value |
|----------|-------|
| **Notion AMA doc** | Page ID: `006325e85f824a3c9d2ddb0887caf548` |
| **Polly channel** | `#announcements` — Channel ID: `C03BYJTHD` |
| **Polly bot user** | `UFFDJ6DRS` (Polly app) |
| **Exec Slack channel** | `#exec-internal` — Channel ID: `CFDQUABPA` |
| **Notion doc URL** | `https://www.notion.so/gorgias/AMA-preparation-document-006325e85f824a3c9d2ddb0887caf548` |

---

## Exec topic-assignment map

Questions are assigned at the **category level** — all questions under a category go to the
same exec. Use this standing mapping to auto-assign.

| Category | Exec | Notion user UUID |
|----------|------|------------------|
| Company strategy & vision | Romain Lapeyre | `4387da15-736b-49d8-801d-3e8bb820933e` |
| AI transformation (company-wide) | Adeline Bodemer | `5f867bed-52ed-4126-b27c-583197aeb9ca` |
| Finance, stock options, compensation | Kunal Agarwal | *(look up via `notion-get-users`)* |
| People, HR, hiring, performance reviews | Adeline Bodemer | `5f867bed-52ed-4126-b27c-583197aeb9ca` |
| Remote work, office policy, wellness, perks | Adeline Bodemer | `5f867bed-52ed-4126-b27c-583197aeb9ca` |
| Workplace & office logistics (WiFi, meeting rooms, facilities) | Adeline Bodemer | `5f867bed-52ed-4126-b27c-583197aeb9ca` |
| Engineering & technical infrastructure | PA Masse | `249d872b-594c-8172-81c3-00022d36c3d3` |
| Sales & partnerships | Josh Roth | *(look up via `notion-get-users`)* |
| Product & design | Max Pruvost / Bora Shehu | *(look up via `notion-get-users`)* |

### Assignment rules

1. **Department-specific AI questions go to the department leader.** E.g., "will AI reduce
   finance headcount?" → Kunal. "How is AI changing the engineering org?" → PA. Only
   company-wide AI transformation questions (e.g., "what's Gorgias's stance on AI replacing
   employees?") go to Adeline.
2. **Key political questions → Romain.** High-visibility or sensitive questions (e.g., AI
   replacing headcount, attendance tracking controversy) may be reassigned to Romain even if
   they fall under another exec's domain. Juliette decides — flag these as candidates and let
   her confirm. When Romain is assigned to a question in another exec's category, tag him
   inline on the question with `<mention-user url="user://4387da15-736b-49d8-801d-3e8bb820933e"/>`.
3. **Ambiguous questions → "To assign" section.** If you genuinely can't determine the right
   exec, place the question in a `## To assign` section at the bottom of the toggle (no
   `<mention-user>` tag). Juliette will assign them manually.
3. The first time you run this skill in a session, resolve any missing UUIDs via
   `notion-get-users` or `notion-search` (query_type: "user") and cache them for the session.

---

## Workflow overview

The skill has five phases plus a late-question sweep. The user may ask you to run all of them
end-to-end, or just one phase at a time. Infer from context which phase is needed.

### Phase 1: Pull questions from Polly

1. **Find the Polly thread.** Search `#announcements` for the most recent Polly AMA post.
   Use `slack_search_public_and_private` with query `"AMA" from:<@UFFDJ6DRS> in:#announcements`
   sorted by timestamp descending, with `include_bots: true`. The parent message is from the
   Polly app (bot user `UFFDJ6DRS`).

2. **Read the full thread.** Use `slack_read_thread` with the parent message's `channel_id`
   and `message_ts`. Set limit high enough to capture all replies (Polly posts each question
   as a separate thread reply).

3. **Parse each question.** Each Polly reply follows this format:
   ```
   New submission to: *[AMA Title]*
   *Status:* :white_check_mark: Public
   Anonymous | <date>
   
   *[Question text — may span multiple bold lines]*
   :thumbsup: Upvote | N
   ```
   
   Extract:
   - **Question text**: everything between the anonymous line and the upvote line, stripped
     of `*` bold markers (you'll re-bold in Notion format)
   - **Vote count**: the integer `N` after `Upvote |`
   - **Submission timestamp**: for ordering within each category

4. **Record pull metadata.** Note the current date + time in ET and the total number of
   questions pulled. This metadata goes into the toggle title (see Phase 2).

### Phase 2: Categorize and write to Notion

1. **Categorize each question.** Map each question to a category using the exec topic-assignment
   map and the assignment rules above. Group questions by category/speaker.

2. **Order questions.** Primary sort: by topic/speaker (categories). Secondary sort within each
   category: by submission date, **oldest to newest** (so execs see questions in the order they
   were asked).

3. **Fetch the AMA Notion doc.** Use `notion-fetch` on page ID `006325e85f824a3c9d2ddb0887caf548`
   to get the current content. Identify where to insert the new toggle.

4. **Build the new toggle content.** The toggle should be inserted as the first item under
   the `## Next AMA` section (or after the H1 header area, before previous AMA toggles).
   
   Structure:
   ```markdown
   ## <mention-date start="YYYY-MM-DD"/> [AMA Title] - [Polly link] — latest update: [date+time ET] ([N] questions) {toggle="true"}
   
   \t## [Category Name] <mention-user url="user://[UUID]"/>
   
   \t- **[Question text]** *(N votes)*
   
   \t- **[Question text]** *(N votes)*
   
   \t## [Category Name] <mention-user url="user://[UUID]"/>
   
   \t- **[Question text]** *(N votes)*
   
   \t## To assign
   
   \t- **[Ambiguous question text]** *(N votes)*
   ```
   
   Formatting rules:
   - The toggle header is an H2 with a Notion date token, the AMA name, a Polly link, and
     the latest update timestamp + question count. Always include `{toggle="true"}`.
   - The **latest update** field shows when the questions were last pulled (date + time in ET)
     and total question count — e.g., `latest update: Apr 11, 2026 2:30 PM ET (15 questions)`.
     This gets updated on every subsequent pass.
   - Each category is a tab-indented H2 with the category name and a `<mention-user>` tag
     for the assigned exec
   - Each question is a tab-indented bold bullet with the vote count in italics after it
   - **Top 3 questions by votes** (across all categories) get a ⭐ prefix: `\t- ⭐ **Question text** *(N votes)*`
   - Questions within each category are sorted by submission date (oldest first)
   - Leave space after each question for answer bullets (execs will fill these in as
     `\t\t- [answer text]`)
   - If any questions are unassigned, place them under a `\t## To assign` section at the end

5. **Write to Notion.** Use `notion-update-page` with `update_content` command.
   Find the right insertion point and insert the new toggle content.

6. **Report to Juliette.** After writing to Notion, share:
   - Link to the Notion doc
   - Number of questions synced
   - Breakdown by exec (who has how many questions)
   - Any questions placed in "To assign" — list them so Juliette can decide

### Phase 3: Post to #exec-internal

**Do not post automatically.** After the Notion doc is updated, draft the Slack message and
share it with Juliette in the conversation first. Only post after explicit approval.

Use the `slack-messaging` skill and `style-slack.md` for formatting. The message should follow
this structure:

```
*🎤 Company AMA — [Date]*

[N] questions synced from Polly → <[Notion doc URL]|AMA prep doc>

Questions are assigned by topic:
- *[Category]* → [Exec name] ([M] questions)
- *[Category]* → [Exec name] ([M] questions)
- *[Category]* → [Exec name] ([M] questions)

Please add answer points (at least 1 bullet per question) before [deadline].
```

Once Juliette approves the message text, use `slack_send_message` to post to `#exec-internal`
(channel ID: `CFDQUABPA`).

### Phase 4: Check answer completeness

**Timing:** Run this on the **business day before the AMA** — typically Friday, since AMAs
are almost always on Mondays. Juliette may also trigger this manually at any time.

1. **Fetch the AMA doc** and navigate to the relevant date toggle.
2. **For each question** (identified by `\t- **[text]**`), check whether there is at least
   one answer bullet underneath it (`\t\t- [text]`).
3. **Report back** with:
   - Total questions vs. answered questions
   - Per-exec breakdown (e.g., "Adeline: 5/7 answered, missing Q3 and Q5")
   - List of unanswered questions with their vote counts (highest votes = most urgent)

### Phase 5: Pre-AMA exec summary

Generate a concise theme summary that Juliette can **share directly with the exec team**
before the live AMA. This is not an internal doc — write it so it's ready to forward.

Structure:
```
*🎤 AMA theme preview — [Date]*

[N] questions submitted. Here's what employees are asking about:

*[Theme 1: e.g., "Office policy & remote work"]* ([M] questions)
[1-2 sentence summary of the sentiment and core ask]

*[Theme 2: e.g., "AI & headcount"]* ([M] questions)
[1-2 sentence summary]

*[Theme 3: e.g., "Compensation & equity"]* ([M] questions)
[1-2 sentence summary]

Top 3 by votes:
1. [Question summary] *(N votes)* → [Exec]
2. [Question summary] *(N votes)* → [Exec]
3. [Question summary] *(N votes)* → [Exec]
```

Group by sentiment/theme rather than by assigned exec — this gives a "what's on employees'
minds" view that helps execs prepare for the live discussion dynamic.

Draft in chat for Juliette's approval before sharing.

### Late-question sweep (2 hours before AMA)

Questions trickle in until the Polly closes. **2 hours before the AMA start time**, do a
final pass:

1. Re-read the Polly thread to pick up any new submissions since the last pull.
2. Add new questions to the existing toggle in the Notion doc (in the right categories,
   maintaining oldest-first ordering within each category).
3. Update the **latest update** timestamp and question count in the toggle title.
4. Update vote counts on all questions (votes may have changed since the first pull).
5. Notify Juliette in chat with the delta: "Added X new questions (total now Y). Updated
   vote counts."

---

## Edge cases

- **Polly thread not found**: Ask the user for the Polly thread link or message timestamp.
- **Questions already synced**: If the date toggle already exists in the Notion doc, treat it
  as an update pass — add new questions, update vote counts, update the timestamp. Don't
  create duplicate toggles.
- **New category needed**: If a question doesn't fit any existing category, create a new one
  and assign to the most relevant exec. Tell Juliette about the new category.
- **Exec UUID not cached**: Use `notion-get-users` or `notion-search` (query_type: "user")
  to look up the UUID. Cache it for the session.
- **Very long questions**: Some Polly questions are multi-paragraph. Keep the full text — don't
  truncate. Execs need to see the complete question to prepare a good answer.
- **Questions with 0 votes**: Still include them — they were important enough for someone to
  write. Just sort them last within their category (oldest-first still applies among 0-vote
  questions).

---

## Notion formatting cheat sheet

These patterns match the existing AMA doc structure. Use them exactly.

| Element | Format |
|---------|--------|
| AMA toggle header | `## <mention-date start="YYYY-MM-DD"/> Title - [Polly](url) — latest update: [datetime ET] ([N] questions) {toggle="true"}` |
| Category with exec | `\t## Category Name <mention-user url="user://UUID"/>` |
| Unassigned section | `\t## To assign` |
| Question with votes | `\t- **Question text** *(N votes)*` |
| Top-3 question (by votes) | `\t- ⭐ **Question text** *(N votes)*` |
| Answer bullet | `\t\t- Answer text` |
| Date reference | `<mention-date start="YYYY-MM-DD"/>` |
| User mention | `<mention-user url="user://UUID"/>` |
