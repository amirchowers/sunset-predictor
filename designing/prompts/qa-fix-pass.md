Read:
- designing/critiques/design-qa-v1.md
- designing/briefs/visual-system-v1.md
- designing/tokens/design-tokens.json
- designing/notes/implementation-v1.md
- sunset_predictor/renderer.py
- render_card.py

Act as the Production Designer for Sunset Predictor.

Context:
The HTML/CSS renderer (renderer.py) is built and working but has QA issues documented in design-qa-v1.md. Your job is to implement the fixes in priority order, verify each one visually, and leave the renderer production-ready.

Tasks — implement in this exact order:

1. P0-1: Add verdict width constraint + text wrapping
   - `.verdict` CSS: add `max-width` and `overflow-wrap: break-word`
   - Test: render with `--verdict "Might catch something decent if you are already outside"` — must wrap, not overflow

2. P0-2: Convert info zone from absolute to flow layout
   - Wrap verdict/separator/WHY/drivers in a single `div.info-block` positioned absolutely, with internal elements using margin-based flow
   - Remove individual `top:` values from info-zone children
   - Test: render with a 2-line verdict — separator and drivers must shift down naturally

3. P0-3: Bump `text.tertiary` to `#8A8480` (4.9:1 contrast)
   - Update both `design-tokens.json` and any hardcoded CSS in renderer.py
   - Update `visual-system-v1.md` palette table to match
   - Test: labels should be visibly lighter but still the lowest tier in hierarchy

4. P1-1: Fix story no-tip vertical void
   - When `tip is None and fmt == "story"`, redistribute spacing so content fills ~50% of canvas, not 25%
   - Test: render `--story --no-tip --score 3 --verdict "Overcast"` — content should not bunch at top

5. P1-2: Score bar visibility at low scores
   - Add subtle accent-colored border or outline to `.bar-track` so bar is distinguishable even at score 2
   - Test: render `--feed --score 2 --no-tip` — bar must be visible

6. P2-2: Add `font-variant-numeric: tabular-nums` to `.sc-num`
   - Test: render scores 2, 7.6, 10 — digit spacing should look consistent

7. Fix tip label margin to use proper spacing (currently hardcoded 8px, should be ~12-16px)

After all fixes:
- Run the full QA test matrix from the bottom of design-qa-v1.md (8 test cases)
- Visually inspect all outputs
- Write updated implementation notes to designing/notes/implementation-v2.md
- Do NOT wire the renderer into the daily pipeline yet — that's a separate task

Rules:
- All visual values must come from design-tokens.json — update the tokens if needed, don't hardcode
- Keep the renderer deterministic and JSON-driven
- Python 3.9 — use `Optional[X]` not `X | None`
- Existing poster.py tests must still pass
- Show me the generated outputs before claiming anything is done
