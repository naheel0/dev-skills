# dev-skills

A set of agent skills for writing dev.to posts in your own voice, auditing what actually worked, and feeding those results into the next draft. Works with OpenCode, Claude Code, and other agents that load `SKILL.md` files.

## Why

Generic writing advice is a prior. Your own posts are the evidence. These skills close the loop:

```
dev-learn.py audit --apply  <--  /dev-audit  <--  analytics + ~/.claude/devto/log.md
        |  promotes winning formulas/tags, demotes losers
        +---------------------->  /dev-post's next draft
```

## Install

```bash
git clone https://github.com/naheel0/dev-skills.git
cp -r dev-skills/dev-* ~/.config/opencode/skills/     # OpenCode
cp -r dev-skills/dev-* ~/.claude/skills/              # Claude Code
cp dev-skills/dev-learn.py ~/.config/opencode/skills/
```

If you install somewhere other than `~/.config/opencode/skills`, set the path so `dev-learn.py` knows where the skills live:

```bash
export DEVTO_SKILLS_DIR=~/.claude/skills
```

## Skills

| skill | what it does |
|---|---|
| `/dev-post` | Turn one raw idea into a full draft, three title options, and a copy-ready block. Never publishes without your "yes". |
| `/dev-human` | Strip AI tells from a draft and score it against a human-sounding check. |
| `/dev-comment` | Write a comment on someone else's post — three angles, one full comment. |
| `/dev-audit` | Post-mortem on your published posts using analytics + `log.md`. Rank by engagement rate, not views. |
| `/dev-learn` | Apply the audit's findings: promote winning formulas/tags, demote losers. |
| `/dev-profile` | Score your dev.to profile out of 100 and rewrite the parts that lose points. |
| `/dev-repurpose` | Turn a long asset (video, newsletter, transcript) into a dev.to article with a canonical URL. |

## First-time setup

Create `~/.claude/devto/`:

```bash
mkdir -p ~/.claude/devto
```

**`voice.md`** — your voice profile. `/dev-post` will ask for three of your own past posts and write this file if it does not exist. Do not skip it; a draft in the wrong voice is worse than no draft.

**`log.md`** — your post history. This is the data `/dev-audit` and `dev-learn.py` read. Start it with this header and append one row per post:

```markdown
# dev.to post log

| date | title | formula_id | tags | cover | canonical | series | published | engagement_rate | comment_ratio | reach_multiple | human_score | audit_rank | first line |
|------|-------|------------|------|-------|-----------|--------|-----------|-----------------|---------------|----------------|-------------|------------|------------|
```

`/dev-post` appends the date, title, formula, tags, and metadata. `/dev-audit` fills in the engagement metrics later. `dev-learn.py` will not change any weights until at least 10 posts are audited.

## The learning loop

After a post has collected data:

```bash
/dev-audit                                              # find what worked
python3 ~/.config/opencode/skills/dev-learn.py audit    # dry-run: show proposed changes
python3 ~/.config/opencode/skills/dev-learn.py audit --apply
/dev-post                                               # next draft uses the new weights
```

`dev-learn.py` never deletes a formula or tag — it drops the weight to 0 and moves it to `archive`. Slop words in `dev-human/slop.json` are left alone; they are voice-specific and need your review.

## License

MIT. See [LICENSE](LICENSE).
