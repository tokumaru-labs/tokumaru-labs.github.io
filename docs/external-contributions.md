# External contributions: scope and evidence

Reviewed on 27 November 2026 (JST). This record supports the founder's personal
contribution history on the English homepage. These are third-party projects,
not Tokumaru Labs products, partnerships, or endorsements.

## PEqualNP

The initial brief described six accepted proofs. Live verification found a seventh
merged PR, so the page records **seven** as of this review.
GitHub's individual PR records confirm `bhcir` as author and `merged: true` for
every entry. Each PR adds the corresponding file under
`lean/PEqualNP/Outside/L_meta_<number>.lean`.

| Lemma | Merged PR | Merge time (UTC) | Merge commit |
| --- | --- | --- | --- |
| L-meta-11119 | [#15164](https://github.com/open-goat/pequalnp-proofs/pull/15164) | 2026-11-25 14:01:45 | `2b3ba8b5768fc6e32dab3de6cfcdba2dcc12cc54` |
| L-meta-10774 | [#15329](https://github.com/open-goat/pequalnp-proofs/pull/15329) | 2026-11-25 14:32:18 | `a5fefe63acc9b7f011b4be86741e7bcd3f40e2da` |
| L-meta-11317 | [#15631](https://github.com/open-goat/pequalnp-proofs/pull/15631) | 2026-11-25 15:37:11 | `1163808d9f37039cb9d66e92c08a830ccb1cbb93` |
| L-meta-12611 | [#16699](https://github.com/open-goat/pequalnp-proofs/pull/16699) | 2026-11-25 17:46:35 | `5647532592e758cd25fee8b076d9d56d27f78bdf` |
| L-meta-14902 | [#18757](https://github.com/open-goat/pequalnp-proofs/pull/18757) | 2026-11-25 18:33:34 | `e91a25fa9a128cc5fbeac7a9929f4b3cd5578e4e` |
| L-meta-14240 | [#19076](https://github.com/open-goat/pequalnp-proofs/pull/19076) | 2026-11-25 18:50:33 | `4f8b846f9784ab75a172e10b58e6a6b34817d626` |
| L-meta-21628 | [#29345](https://github.com/open-goat/pequalnp-proofs/pull/29345) | 2026-11-26 17:34:26 | `3e30f2d3524b8dbf2445019eba59391cb2b6ae29` |

The [public contributor snapshot](https://data.pequalnp.com/data/contributors.f5562524bedb.json)
also records all seven lemma IDs for `bhcir`. It was referenced by
[head.json](https://data.pequalnp.com/head.json) with `generated_at` of
`2026-11-27T00:27:08.072Z` (09:27 JST), 950 contributors and no recorded breakthrough.

Proof-count rank in that snapshot: **180 of 950**. This is the proof-count view,
not the site's points ranking, an assessment of mathematical importance, or a
permanent rank. Reproduce the ordering used by the site's
[ranking code](https://pequalnp.com/assets/5e3243b2e55c/js/contributors.js):
descending `steps`, ascending `first_proof_at`, then ascending GitHub handle.
The homepage keeps the date and metric beside the rank inside the proof details.

The [repository README](https://github.com/open-goat/pequalnp-proofs#readme)
describes machine-checked individual lemmas, not a resolution of P vs NP.
This portfolio review verified public acceptance records and file identity; it
did not independently rebuild the Lean proofs. No proof of P = NP or P != NP is
claimed. Recheck both the PR records and a dated contributor snapshot before
updating the count or rank.

## Localization history

Public links are evidence only where explicitly labeled as such. Crowdin project
pages identify the projects; they do not independently establish the founder's
historical role. Private correspondence was reviewed to establish the limited
facts below. No messages, mail links, attachments, private identifiers, or contact
details are included in this repository.

| Project | Supported scope | Evidence reviewed | Public reference |
| --- | --- | --- | --- |
| Battleship | Japanese localization, credited as Tokumaru Ogawa | Official contributor file lists the name under Translators with Japan | [Official humans.txt](https://battleship-game.org/static/humans.txt) |
| iNaturalistMobile | Japanese translation and proofreading | January 2015 translation-context discussions and Crowdin proofreader promotion dated 2015-02-09 UTC | [Crowdin project](https://crowdin.com/project/inaturalistios) (context) |
| AIMP Remote Control | Japanese translation and proofreading; a Japanese build provided by the developer | Crowdin team approval dated 2015-06-16 UTC, proofreader promotion dated 2015-06-18 UTC, and Japanese-build notice dated 2015-06-30 UTC | [Crowdin project](https://crowdin.com/project/aimp-remote-control) (context) |
| Messenger for LoL | Japanese localization delivered to the developer, with subsequent wording updates | Developer correspondence in March-April 2016, final handoff on 2016-03-24 JST, and follow-up updates | Private records only |
| Reddit | Membership in the Japanese translation team | Crowdin team approval dated 2015-01-07 UTC | Private records only; completed translation volume and a proofreading role are not established |
| Livecoding.tv | Japanese proofreader appointment and Japan-market feedback | Support confirmation dated 2015-11-25 UTC and December 2015 feedback correspondence | Private records only; completed translation volume, market results, and a commercial role are not established |

The build notice supports the existence of a developer-provided Japanese build,
not a current download, an independently tested release, or audience statistics.
Historical roles are not presented as current appointments. Uncorroborated history
and personal anecdotes are outside this portfolio section.
