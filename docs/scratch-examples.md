# Recreating Scratch examples in Python

The Scratch Team's [starter-project catalogue](https://github.com/scratchfoundation/scratch-www/blob/develop/src/views/starter-projects/starter-projects.json) links public, remixable projects with visible block source. This chapter starts with two of those projects and separates a runnable adaptation from a translation plan.

## Hide and Seek: runnable adaptation

Original: [Hide and Seek](https://scratch.mit.edu/projects/10128368/) by **Scratchteam**. The original block graph was inspected on 2026-10-11.

The target alternates between hiding and appearing at random positions. Clicking it increments the score, plays a sound, and relocates it. The Python adaptation keeps those mechanics with original geometric artwork and a generated chime. It omits the introductory speech bubble and keeps click relocation within the same visible bounds as the timed loop.

### Map blocks to Python

| Original Scratch sequence | itchy description |
| --- | --- |
| Green flag; set score; go to center; show | `on_start(reset_round, ...)` |
| Forever; hide; wait; choose random x/y; show; wait | `forever(hide_then_appear)` |
| When sprite clicked; change score; sound; relocate | `on_click(found_target)` |
| Pick random | `random_number(low, high)` |

### Name the sequences with lists

The runnable source is included directly, so the book and executable example stay aligned:

```python
--8<-- "games/hide_and_seek.py"
```

`reset_round`, `hide_then_appear`, and `found_target` are ordinary typed lists. `relocate` is a single reusable command whose random reporters are evaluated by Scratch on each execution, not when Python constructs it.

### Run and test

These examples live in the itchy source repository. Run `uv sync` and activate `.venv` before using the commands below. For your own project, use `itchy init` instead.

```sh
itchy run
```

Select **Hide and Seek** from the menu, then click the visible target. Build its standalone export with `itchy build`; the file is `dist/hide-and-seek.sb3`.

Browser tests load that exported project, wait for the target to appear, click its rendered position, check the score, and restart. Timer and randomness behavior is tested in the browser; the headless tick adapter does not control wall-clock waits or random seeds.

### Attribution

`games/hide_and_seek.py` is marked **CC BY-SA 2.0**, with the original project and author credited in its header. The [Scratch website's historical terms source](https://github.com/scratchfoundation/scratch-www/blob/develop/src/views/terms/terms.jsx) documents the remix license used for shared projects of this period. The [license text](https://creativecommons.org/licenses/by-sa/2.0/) describes attribution and share-alike terms. No original costume or sound files are bundled in this adaptation. This example license does not assign a license to the rest of itchy.

## Pong Starter: verified translation plan

Original: [Pong Starter](https://scratch.mit.edu/projects/10128515/) by **Scratchteam**, whose project notes credit **@natalie**. The original block graph was inspected on 2026-10-11.

| Original behavior | Translation status |
| --- | --- |
| Ball initializes at a position and direction | Position supported; direction command still needed |
| Ball moves and bounces at edges forever | Loop supported; directional movement and edge bounce still needed |
| Paddle follows mouse x | Mouse-position reporter and x setter still needed |
| Touch paddle; sound; randomized turn; move away | Touching, sound, conditions, and random reporters supported; turning still needed |
| Touch losing color; stop | Color sensing and stop command still needed |

This is a roadmap derived from the actual source, not a runnable Pong port. Implement the missing typed operations, translate each independent event script, then test paddle movement, contact response, loss, and restart before including the exported game in the showcase. Preserve the original author and project attribution if adapting its scripts or assets.

## Add another recreation

Choose a source with visible scripts and an explicit reuse license. Record the project URL, author, inspected version/date, and any additional credits. Compare its block graph against the supported API. Replace or attribute assets, document intentional changes, and add behavioral tests. Prefer small complete recreations to snippets that silently omit important scripts.
