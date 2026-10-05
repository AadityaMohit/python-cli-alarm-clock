# Submission checklist & email draft

Not part of the app — a helper for submitting. Delete before pushing if you'd
rather not include it (it's harmless if you do).

## What to submit (to akanksha@btr.group, within 24h)

1. **GitHub repo** (source + README) — push this folder, make the repo public
   or invite the reviewer.
2. **Screen recording with narration** — see `docs/RECORDING-SCRIPT.md`. Upload
   to Loom / YouTube (unlisted) / Google Drive and include the link.
3. **CV** — attach as PDF.

Subject line (exactly as requested):

```
Senior Software Engineer- [Your Name]
```

## Push to GitHub

The repo is already initialized and committed. Just create the GitHub repo and push:

```bash
cd "alarm-clock"
git remote add origin https://github.com/<you>/alarm-clock.git
git push -u origin main
```

Then, so the CI badge in the README goes live:
1. In `README.md`, replace both `OWNER/REPO` occurrences with `<you>/alarm-clock`.
2. Commit and push: `git commit -am "Point CI badge at repo" && git push`.
3. Confirm the Actions tab shows a green run (tests on Linux + Windows, Py 3.10-3.13).

## Email draft

> Hi Akanksha,
>
> Please find my submission for the Senior Software Engineer build exercise — a
> dependency-free Python CLI alarm clock.
>
> - **Repo:** https://github.com/<you>/alarm-clock
> - **Recording (with narration):** <link>
> - **CV:** attached
>
> I focused on the engineering decisions over feature count. The brief had no
> spec, so I started by framing the hidden decisions (how it rings, one-shot vs
> recurring, storage given "no database", dependencies) — written up in
> `docs/DESIGN.md`. The core is a pure, fully-tested scheduling function behind
> an injectable clock; `docs/AI-COLLABORATION.md` describes how I directed and
> reviewed the AI, including the due-detection bug I caught in review. The
> recording walks through all of this and shows the 57-test suite and a live
> alarm firing.
>
> Thanks for the exercise — I enjoyed it. Happy to walk through any part.
>
> Best,
> [Your Name]
> [phone] · [GitHub] · [LinkedIn]

## Final pre-send check
- [ ] `python -m pytest` is green on a clean clone.
- [ ] README renders on GitHub; links to `docs/` work.
- [ ] Recording link is accessible (test in an incognito window).
- [ ] Subject line matches the requested format exactly.
- [ ] CV attached as PDF.
