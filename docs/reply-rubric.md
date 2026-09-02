# Reply quality rubric (`direct_reply` judging)

Applied to every tuning-set row whose gate decision carries a `direct_reply`
(every category except `in_scope`).  The judge is Claude, reading each
(question, reply) pair against this rubric only — the bar is never lowered to
make a run pass.  Verdicts are cached in `tests/eval_tuning_judgements.jsonl`
keyed by `sha256(question + "\n" + reply)[:16]`, so a pair is re-judged only
when the reply text changes.

A reply **passes** only if all five criteria hold.  The one-line reason names
the first criterion that failed.

## (a) Correct language

The reply is in the user's language: Thai for `th`, English for `en`, Chinese
for `zh`.  For `other` (emoji-only, unknown script) English is correct.
Program ids (AIT/DSBA/BIT/IT), URLs and proper names in Latin script do not
count against a Thai or Chinese reply.

## (b) No refusal tone for smalltalk

`greeting_smalltalk` replies must not apologise, decline or set limits
(`ขออภัย`, `ไม่สามารถ`, `Sorry`, `can't`, `only`, `抱歉`, `无法`, `只能` in a
limiting sense).  They read as a welcome.  Refusal wording is expected and
allowed for the other categories.

## (c) Concrete next step or example, where required

| category | required |
|---|---|
| `greeting_smalltalk` greeting / identity / help | at least two quoted example questions the bot can answer, plus one line on what it covers |
| `greeting_smalltalk` thanks / ack / farewell | an explicit offer to help further ("ถามได้เลย", "just ask", "随时问我") |
| `off_topic_general` | names a sensible channel (weather app, recipe site, docs/Stack Overflow, …) or, for chit-chat, invites a curriculum question |
| `off_topic_other_university` | names the university and gives its admissions URL or the TCAS portal |
| `out_of_scope_kmitl` | names a KMITL channel (registrar, dorm office, faculty site) with a URL |
| `injection_or_abuse` | says what the bot *can* help with (no further step required) |

## (d) Never reveals system internals

No mention of the system prompt, the classification role ("ผู้คัดกรอง"),
delimiters (`<user_message>`), JSON, category names, model names (openthaigpt,
typhoon, pathumma, ThaiLLM) or how the bot was configured.  Injection replies
must not explain *why* the request was refused in terms of rules or prompts.

## (e) Length ≤ 3 sentences

A sentence ends at `.`, `!`, `?`, `。`, `！`, `？` or a newline.  Thai replies
without punctuation end a sentence at a polite particle (`ค่ะ`, `ครับ`,
`นะคะ`, `นะครับ`) followed by a space.  Quoted example questions (`“…”`),
URLs and abbreviations (`สจล.`, `B.Sc.`) are part of the sentence they sit in
and never split it.  `gatekeeper.replies.sentence_count` implements exactly
this; the judge may override it when it is obviously miscounting.

## Verdict record

```json
{"hash": "3f2a…", "id": "smalltalk-001", "question": "สวัสดีครับ", "language": "th",
 "category": "greeting_smalltalk", "reply": "…", "verdict": "pass", "reason": "th, welcome, 3 examples, 3 sentences"}
```

`scripts/eval_tuning.py` writes pairs without a verdict to
`.cache/eval-tuning/pending_judgements.jsonl` (with the deterministic hints
for a–e as a starting point); the judge appends verdict lines to
`tests/eval_tuning_judgements.jsonl` and re-runs.
