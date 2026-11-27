---
name: ab-test-flow-video
description: Make a one-page animated explainer video (MP4, 1080x1350) of an A/B test — six blocks (Design, Randomize, Allocate, Measure, Analyze, Decide) that stay on one page and animate in turn — for LinkedIn or slides. Use when asked for an A/B test video, an experiment walkthrough animation, or a new variant of the existing one (different feature, metric, numbers or theme).
---

# One-page A/B test flow video

The template is `visuals/ab_test_flow/ab_test_flow_paper.html` (light "paper" theme).
`ab_test_flow_onepage.html` is the same layout in a dark theme. `render.js` turns either
page into an MP4. Copy the template, change the story and numbers, verify, render, review.

## How the template works

- A single `<canvas>` (1080x1350, 4:5 portrait — the largest feed format on LinkedIn mobile).
- Everything is drawn by `render(t)` from the time `t` alone (no timers, no randomness at
  draw time; dots use a seeded `mulberry` RNG). That makes frame-by-frame rendering exact.
- The page exposes `window.renderAt(t)`, `window.TOTAL` and `window.ready` (fonts loaded).
  Without `?render=1` it plays in a browser with pause and a scrubber.
- `BLOCKS` (titles, subtitles, grid positions), `TIMES` (`[start, end]` seconds each block is
  active) and `CONTENT` (one `cXxx(lt)` function per block, `lt` = seconds since that block
  started, drawing in block-local coordinates 0..474 x 0..330).
- A block is *pending* (dashed placeholder), *active* (dark border, content animating) or
  *done* (green check, content frozen at its final state — so every `cXxx` must look final
  for any `lt` past its duration).
- The numbers live in constants near the top: `N_ARM`, `DAYS`, `CLICKS_A`, `CLICKS_B`,
  `CUM_A`/`CUM_B` (cumulative daily metric, illustrative path that must end at the final
  values), plus literals inside the block functions (sample size, CI, z, p, lift).

## Steps

1. **Copy** `visuals/ab_test_flow/ab_test_flow_paper.html` to a new name in the same folder
   (keep the originals). Change the `<title>`.
2. **Compute every number with this repo's package**, never by hand:
   ```python
   from abtest import sample_size_proportions, two_proportion_ztest

   n = sample_size_proportions(baseline, mde, relative=True)  # per arm
   r = two_proportion_ztest(conv_a, n_a, conv_b, n_b)  # B - A
   # effect, ci_low, ci_high, statistic (z), p_value; relative lift = effect / p_a
   ```
   For a continuous metric use `welch_ttest`, and `sample_size_means`. Run to a round
   number of users per arm that is at least `n`, and spread it evenly over the days.
3. **Edit the story**: header subtitle and buttons, hypothesis, metric definition, the four
   plan tiles, measure labels, the CTR path, analysis curves (means and standard errors
   `sqrt(p(1-p)/n)`), the CI bar, the stat chips and the decision tiles. If the result is
   not significant, change Decide to "Don't ship" and the verdict chip accordingly.
4. **Render stills and look at them** before the full render:
   ```bash
   cd visuals/ab_test_flow
   PAGE=<new>.html node render.js --stills <scratch-dir> 14 20 31 41 58
   ```
   Check each block while active and at the end (t=58 is the finished page).
5. **Render the video and a thumbnail** (about 2 minutes; Playwright + ffmpeg):
   ```bash
   PAGE=<new>.html node render.js <new>.mp4 30
   ffmpeg -y -sseof -0.1 -i <new>.mp4 -frames:v 1 <new>_thumbnail.png
   ```
   `render.js` reads the canvas with `toDataURL`, so the output size is the canvas size.

## Story consistency checklist (these were real bugs once)

- **Metric definition matches the test.** A two-proportion z-test counts *users who
  converted* out of users exposed (binary per user) — say "users who clicked", not "clicks".
- **Randomize shows shares, not small raw counts.** The animated dots are a balanced,
  shuffled list so the share wobbles early and lands exactly on 50.0 / 50.0, matching the
  Allocate split and the SRM check. A 43-vs-28 counter contradicts the whole story.
- **Totals add up.** users/day x days = users per arm; the safety ramp is *pre-launch*, so
  it does not eat into the measured days.
- **The noisy early days are real.** Keep day 1 on the "wrong side" (control ahead) so the
  "don't peek" callout is true, and make the path converge to the final values.
- **Every on-screen number traces to step 2** (sample size, per-day users, final rates,
  absolute and relative lift, CI ends, z, p).
- **Each animation finishes inside its block's time window**, so the frozen "done" state
  shows final values (e.g. the share counters end at 50.0%).
- **No text overflow**: check the narrow variant cards, the chip rows and long labels.

## Design rules

- Colour has one meaning each: **blue = treatment (B) only**; control (A) is neutral grey;
  highlights, connectors and the difference/CI are ink; green only means "passed" or
  "significant"; amber only for warnings. Never use the treatment colour as a UI accent.
- Paper palette: background `#F6F3EC`→`#ECE8DE`, cards white with soft shadows, ink
  `#15171C`, muted `#6B675F`, B `#2F5BFF`. Fonts: Inter (text) and JetBrains Mono (labels,
  numbers); both are installed locally, so don't load web fonts.
- Keep text at 11px or larger. Big numbers carry the story; labels are supporting.
- Everything stays on one page; motion shows progress (active block, filling connectors,
  a light travelling the flow at the end). The last seconds hold the complete page, which
  doubles as the thumbnail.

## Deliver

Send the MP4 and thumbnail to the user, note that the thumbnail should be set as the custom
LinkedIn thumbnail (the first frame shows empty blocks), and commit the HTML, MP4 and PNG
under `visuals/ab_test_flow/`.
