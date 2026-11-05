# EraSight: IMAGE B reference implementation

The supplied IMAGE B is the visual specification. No direction draw or new design was introduced. At 1800 x 873, the hero now measures x=40, y=191.8, width=1720, height=640. The copy starts at x=92; the CTA starts at y=729.6. These were compared visually with the inline target after each screenshot pass.

## Five corrected mismatches

| Feature | Before at 1800 x 873 | Target / final correction |
| --- | --- | --- |
| Frame | Hero x=128, width=1544 | Hero x=40, width=1720 |
| Copy / navigation | 80px headline, small controls, copy x=160 | Reference-scaled 112px headline, copy x=92, 50px navigation pills |
| Graph proportions | Small scattered volume far right | Large spherical rim and depth volume, central hub near x=1030/y=560 |
| Lighting / density | Weak hub, small halos, thin sparse appearance | Crisp cores, shader halos, central pink-white flare, layered evidence edges and subdued decorative scaffold |
| Gradient | Uniform saturated field with weak diffusion | Curved blue boundary, dark cobalt behind graph, icy left and pale bottom-right fade |

The page was captured before, after two correction passes, and from the final production build. Screenshots live in `.taste-skill/pixel-reference/`. The final exact-viewport image is `final-1800x873.png`; responsive captures cover 1440, 768 and 390 pixels. The supplied target is inline in the conversation, not a local image file, so no automated bitmap difference score is claimed.

## Data integrity and rendering

Selectable nodes and all analytical edges still come exclusively from CaseResult.graph_data. The default demo has 38 nodes, 37 evidence relationships and six actual alert nodes. The reference has four visible alerts; real alert statuses were preserved.

The latest brief explicitly permits non-evidence guide geometry. A separate LightScaffold layer adds faint local chords and radial light. It cannot be selected, is excluded from relationship counts and path traversal, and disappears while filtering or inspecting a path. Find a node explains that it is decorative. No fixture edges or findings were added.

The deterministic layout uses an outer rim plus a three-dimensional inner shell. Instanced cores, buffered lines, merged edge-glow tubes and shader halos render it without per-frame React state changes. The identity hub has a separate pink-white optical flare. Rotation takes approximately 120 seconds; ordinary glow cycles take 4-7 seconds, hubs 5-8 seconds and alerts 3 seconds. Pause, reduced motion, hidden tabs and offscreen state stop ambient motion.

## Controls and limits

The desktop hero matches the reference's resting composition: graph controls appear on hover or keyboard focus, while Find a node remains visible. Mobile controls remain visible. Search, filters, case selection, evidence details and the SVG/WebGL-loss fallback remain available. The API contract, dataset, engine and integrations are unchanged.

Production build and all six regression tests pass. Browser checks cover pause/resume, rotation/zoom/reset, alert filtering, evidence details, search, case switching and reduced motion. Responsive inspection reports zero failures, with warnings for the reference's white-on-blue selected navigation, mixed technical typefaces and compact labels. The Three.js bundle remains large (about 261 kB gzip). Live Slack/email delivery is not tested.

Additional browser checks passed: native pointer picking of the central node, keyboard revelation of desktop controls, quarter-turn capture and WebGL context-loss fallback.
