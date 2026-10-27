# BJJ Game — Approved Visual North Star v1.0

**Approved by project owner:** 2026-10-27  
**Status:** Approved ART DIRECTION target; not an implementation milestone or gameplay-mechanics approval.  
**Original approved reference:** user-supplied image `1793126467211.png` in the October 27, 2026 art-direction discussion. **The image binary is not yet checked into this repository**; retain the accompanying `BJJ_Visual_North_Star_v1.zip` and add the original under `docs/art/references/visual_north_star_v1.png` in a separate asset upload. Do not substitute a regenerated approximation.
**Reference SHA-256 (of retained source image in art package):** `7308cb442e1def76706d8994e08da8673bc357ef383148e16cafd2dc82b39fac` (the packaged file named .png contains JPEG data; preserve or convert deliberately).

## One-sentence art target

**Modern pixel-textured 3D BJJ fighters:** Blender-authored, rigged 3D athletes with hand-painted pixel-cluster skin, hair, clothing and environmental textures; ink-like dark contour lines; expressive anime/cartoon faces; credible grappling anatomy; and a coherent dramatic martial-arts atmosphere.

## Approved direction

1. **3D source and rigging:** Blender is the character authoring tool. Actual 3D meshes and skeletal animations enable customization, directional grappling and reuse. The texture is drawn in a pixel-art language **on the 3D surfaces**, not just a global low-resolution screen filter. This target does not mandate a fully 3D playable presentation before the existing 2D-first milestone.
2. **Surface design:** Intentional visible pixel clusters, stepped painted shading and selective dark outlines, not photorealistic pores, glossy skin or smooth generic PBR. Test nearest filtering and UV/texel consistency; do not assume one resolution works for every face and grip.
3. **Anatomical clarity:** Both fighters' hands, underhooks, hips, legs, top/bottom orientation and critical submission contacts must remain readable. Dramatic timing only *after* technically correct BJJ blocking.
4. **Character system:** One customizable player fighter (not the eccentric Brazilian NPC). White, Black and Asian examples demonstrate appearance possibilities, not ancestry-locked systems. Predetermined face chosen at creation remains permanent; wide hair and skin-tone options, scars, tattoos and basic modular no-gi rashguard/shorts options.
5. **Hair:** Puerto Rican and Black hairstyle references include fades, low tapers, shape-ups/line-ups, afros, twists, cornrows/braids and locs. Longer hair is automatically secured for grappling where appropriate.
6. **Physique:** Three key visual states of the same underlying fighter: **lean (more visibly defined)**, **athletic**, **husky (small visible belly)**. The player picks an initial state; training and diet gradually, reversibly evolve physique. No body sliders.
7. **Personalities:** Archetype-driven posture and gestures, exaggerated but context-appropriate expressions and recognizably different named opponents. This is a cosmetic art direction, not new combat AI.
8. **Initial modeling proof:** Build **one male athletic greybox** in Blender and instantiate it twice as independent actors; validate stance → hand fighting → underhook → whizzer, re-pummel or disengage, from side and three-quarter cameras at deliberate and snappy timings. Verify left/right mirroring rather than presuming it is always safe.
9. **Environments:** The dark academy/tournament lighting in the board is mood inspiration. Isometric perspective, exact UI layout, lighting, hairstyles, clothing graphics, named characters and exact camera remain open.

## Important project-source boundary

`AGENTS.md` currently states that the first playable frontend is **2D-first stylized two-fighter positional art** (Issue #40) and treats 3D greybox as test material, superseding the Master Development Guide's older v10.4 3D gameplay preference. This new North Star **does not silently reverse that production choice**. It governs the approved *look* of future Blender/3D character and material work, while runtime rendering and release-sequence changes require a distinct owner-approved design slice. The deterministic engine remains authoritative and never takes mechanical outcomes from animation or framerate.

## What this approval does NOT finalize

No final mesh topology, animation clip quality, material/shader implementation, pixel resolution, outline method, asset triangle budget, camera, HUD, character face, tattoos, skin palette, or individual combat pose is certified by a concept image. AI-generated contact poses require separate BJJ technique review.

## Art review checklist

- Does the character read as **3D with pixel-painted textures**, rather than smooth generic 3D or screenwide pixelation alone?
- Are the two fighters' identities, contact points and positions visible at the intended camera distance?
- Is the lean / athletic / husky progression recognizably different, including the husky belly?
- Are selectable appearances and hairstyles treated as interchangeable customization, not stereotyped classes?
- Is a proposed stylistic departure explicitly marked as an experiment rather than replacing the approved North Star?
- Does the asset avoid gameplay-rule, parity or deterministic simulation changes?

## Recovery and provenance

This document is the canonical **text** specification. It was recorded to preserve the 2026-10-27 approval across conversations. To fully restore the original *visual* reference after chat deletion, upload the exact archived image to `docs/art/references/visual_north_star_v1.png` and change the link here to that repository path. Until that upload is verified, this document is **not a complete archival copy of the original picture**.
