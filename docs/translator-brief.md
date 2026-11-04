# Translator brief - Black/Matrix + (PlayStation, 2000)

You translate part of the Japanese script of Black/Matrix +, a dark tactical RPG with a religious, morally inverted world, into English for a fan patch. Abel, a silent amnesiac slave, fights the church that rules the world, for love, the worst crime there is.
Work only on the batches named in your dispatch, one at a time in the order given, each to a passing check before the next. Do all translation yourself; do not dispatch subagents.

## Read first
1. `docs/synopsis.md` - the world, plot, routes and late reveals. Don't give a reveal away early; keep early lines consistent with what comes later. **The morals are inverted: read its first section.**
2. `docs/style-reference.md` - character voices and approved example pairs. Match this voice.
3. `work/tl/terms_<batch>.txt` - binding glossary rows for this batch (full table in `glossary.md` if you need more).

## Input: `work/tl/<batch>.tsv`
`id<TAB>speaker<TAB>form<TAB>limit<TAB>Japanese`
- form: dlg (a portrait in the box), narration, choice, menu, name.
- speaker comes from the portrait; blank means no portrait. `faceN` has no name: read the line. Trust the text if it disagrees (`docs/synopsis.md` §Portraits).
- ` / ` separates the lines of one box. Translate the box as one utterance; the build re-wraps it, so don't reproduce the breaks.
- Lines are in story order and scenes run on. `# script N` boundaries aren't shown: an id `s64:0039e` is script 64. **Many scenes appear once per master (six versions of one beat in a row), each in that master's voice**: keep them parallel but give each its voice.
- The same character may speak with a slightly different tone by master route; a line with `妹` and another with `弟` are route variants: translate each as written.

## Output: `work/tl/<batch>.out.tsv`, written with your file-write tool (not a shell heredoc)
`id<TAB>English`, every input id exactly once, same order. Plain ASCII: straight quotes, `...`, `--`; no tabs inside the English, no Japanese or fullwidth characters, no `\uXXXX`. Write `\n` only where a break must fall (rare; lists, a verse, a menu row). The build wraps at spaces.

## Limits
`limit` is a hard limit the checker enforces.
- `17x3` = a portrait box: pages of 3 rows of 34 letters (last row 32). `19x3` = no portrait: 3 rows of 38 (last 36). `19x2` = 2 rows. **One page is about 95 letters in a portrait box.** Past that the game waits at an arrow and pages by itself, so a line may run onto a second page when the meaning needs it (2 pages at most). Most lines should stay on one page: cut filler, not beats, and let a long speech take the second page rather than lose content. Dry-run a long line: `python -X utf8 tools/batches.py fit "text" --box 17x3`.
- `38x2` etc. on a menu or description = rows of that many letters; the rows may be split with `\n` where the Japanese breaks them, or left to fit (the checker counts total letters here).
- `12ch`, `16ch`, `30ch` = letters for one field. Names, items and enemies have the least room: `12ch` means 12 letters, no more. Don't abbreviate a name; report it `LONG:`. (Ruling: engine before abbreviation, so the controller may find room.)
- `{0020}` Abel's name, `{0021}` the master's name, `{0023}` an item: keep each exactly as in the Japanese, once each. The checker counts one as 12 letters. Don't glue a suffix to one.

## Validate
Run `python -X utf8 tools/batches.py check <batch>` from the repo root and fix every reported id until it prints OK. Don't edit anything else.

## Style
- Faithful: keep the information and order of ideas; adapt idiom, not meaning. Don't add details the Japanese doesn't state; don't summarise or skip. Adapt wordplay so the joke still lands (no translator notes).
- Keep the speaker audible. JP register markers carry voice and must turn into English devices, not vanish: old men's じゃ/のう/わし ("eh?", "my boy", "I daresay"), rough men's ぜ/ねぇ/っス ("ain't", "ya", "dammit", clipped grammar), feminine かしら/わよ/のね ("I wonder...", "you know", "dear"), whines and drawls (〜ぅ/なぁ: "but Mooom", stretched words). A line any speaker could have said is a mistake.
- Use names and terms exactly as in the glossary. Never abbreviate to fit. If a line can't fit the limit without losing meaning, say the most important part and report it as `LONG: id`.
- Honorifics stay, hyphenated: -san, -sama, -kun, -chan. Western name order. Punctuation: 「」 and 『』 -> "...", ＜＞ dropped, ・・・ -> `...`, ！？ -> `!?`, ！！ -> `!!`, ！！！ -> `!!!` at a real climax. Thought lines in （） stay in ( ).
- Sound effects in English letters, loud ones in capitals. Screams stay screams: `Gyaaaah!!`, not "He screams".
- Placeholders: no a/an right before a name; no ordinals after a number the game draws.
- Morals stay inverted, as in the synopsis: "wicked" and "sinful" as praise, "hypocrite" as an insult, "love" as a crime. Never soften or explain it. This game is sexual and violent in theme (lust, slavery, incest in the lore, all among adults or as the game presents it): keep tone and meaning, not more explicit than the Japanese. If a line sexualises a child, don't translate that part: write the nearest non-sexual sense and report `UNSURE: id`.

## Consistency
Never edit `glossary.md`. For a recurring name or term not in it, pick a form, use it consistently, and report it.

## Report (reply with only this)
Files written and entry count; then any lines: `NEW TERM: jp -> en`, `UNSURE: id - note`, `LONG: id - note`.
