# Home cinematic talking head with a phone

Target look: George Alexander, "If nobody watches your videos, do this." (Nov 2026). Full analysis: `planning/research/2026-11-05-reference-george-alexander.md`.

**The point:** about 80 % of his look comes from the room and the light, and only about 20 % from the camera and the grade. A new phone in a flat, bright room still looks flat. Fix the set first and buy a phone last.

## What makes his frame (measured on his frames)
| Thing | His frame | Our 007 / 008 frames |
|---|---|---|
| Background brightness vs face | Room **darker** than face (frame average luma ~76/255) | Wall **brighter** than face (008: wall 177, face 139) |
| Depth | 2 to 3 m of room behind him, background soft and out of focus | Curtain or wall right behind the chair |
| Light on face | One soft light from the side: one cheek brighter than the other | Flat front light, no shape |
| Practical lights | Warm lamp in the back right, cool window light on the left | None |
| Colour | Muted room, cool shadows, warm skin | Strong teal curtain or pink-red wall |
| Foreground | A plant at the frame edge, out of focus | None |
| Framing | Chest-up medium shot, eyes about 1/3 from the top, lens at eye level, slightly off centre | Wider shot, mic stand in the frame |

## Set (free, do this first)
1. **Turn the chair around** so the long side of the room is behind you. Sit **2 to 3 m from the back wall**. Distance is what makes the background go soft and dark.
2. **Switch the ceiling light off.** It flattens everything.
3. **Key light:** a window or one soft light **45° to one side and a bit above your eyes**, about 1 m from your face. The far side of your face should be a bit darker, not black.
4. **Background darker than you:** no light aimed at the wall. Close the curtain behind you if a window is there.
5. **One warm lamp behind you** (any table lamp with a warm 2700 K bulb), in the frame, at the side. One small cool light (a monitor, an LED strip set to blue, the window at dusk) on the other side gives the warm/cool split.
6. **Three things in the background:** a plant, a frame or poster, a shelf with a few objects. Not a bed, not cables, no busy pattern.
7. **Plant at the frame edge** close to the camera, so it is out of focus. Free depth.
8. **Mic out of the frame:** boom it from above or below the frame, or use a clip mic.
9. **Clothes:** solid, mid-tone, no logos (denim blue, olive, rust, grey). Not black, not white, not the same colour as the background.

## Phone settings
- **Main 1x lens only** (never ultra-wide, never selfie camera). Step back and use 1x or 2x so the face is not distorted.
- **4K 30 fps**, landscape, on a tripod at eye level, about 1 to 1.3 m from you.
- **Lock everything:** exposure, focus and white balance (about 4500 to 5000 K). Free app *Blackmagic Camera* (iPhone and Android) gives manual control: shutter 1/60, ISO as low as the light allows, lock WB.
- Expose for the face: face a bit bright is fine, background must stay darker. Use the zebra/histogram if the app has it.
- **Cinematic / portrait video mode:** try one 10 s test only. Fake blur often cuts into hair and glasses edges; real distance from the wall is better.

## Buy in this order (cheapest gain first)
1. One soft LED panel or small softbox with a stand (key light). Biggest single upgrade.
2. A warm practical lamp + a small RGB LED (background accents).
3. Clip or shotgun mic out of the frame (audio matters more than picture).
4. A plant and one or two frames for the background.
5. Only then a newer phone, or a used mirrorless camera with a fast lens (f/1.8) for real background blur.

## Grade
Use the `home-cinematic` preset: put `"cam_preset": "home-cinematic"` in `03-edit/shots.json`, or run
`./color-grading/preprocess.sh --preset home-cinematic <clip>`. It mutes everything except skin, cools the shadows, warms the
highlights and adds a soft vignette. Test on 007 and 008 frames: `planning/research/ref-george-alexander/grade-before-after.jpg`.
It helps, but it cannot turn a bright flat wall into a room. The set does that.

## 10-second test before every new set
Record 10 s (talk, turn your head, move a hand), send it. Claude measures face vs background brightness and checks for:
background darker than the face, one side of the face shaped by light, skin not grey or orange, no mic or cables in frame.
