## Strategy: a turret on the left wall

Nothing here has been run, so the design and weights rest only on my reasoning from the source code.

**Position:** The network first moves left to the wall on the surface row, then presses right once. This puts the front at column 1, the back at column 0, and the submarine facing right. It never presses left or right again, so it only has to solve a vertical problem:
- **Enemies:** every enemy at column 2 or beyond can be shot along its row, including those moving away.
- **Divers:** every diver crosses column 1, so waiting in its row collects it.

**Behaviour, from highest priority to lowest:**
1. **Surface row:** align, then dive when row 1 is clear near the wall.
2. **Blocked rows:** never move into a row with danger in columns 0–2.
3. **Surfacing:** go up only if oxygen is below 40 and the gauge proves there is a diver on board. It also goes up at oxygen below 60 if the gauge shows 6 divers.
4. **Dodging:** leave the row if an enemy bullet is in columns 2–4 or any danger is in column 0.
5. **Firing:** fire or hold if the row has an enemy or a diver about to arrive.
6. **Hunting:** move toward a target below, otherwise a target above. Row 1 is not hunted because a repeated "up" there could surface with no divers.

**First layer:**

| Units | Computes |
|---|---|
| 0–6 | Player in row r (2–8) and a target in that row |
| 7–13 | Player in row r (2–8) and an immediate threat in that row |
| 14–21 | Player in row r (1–8), with an analog level encoding whether the rows above and below are blocked |
| 22–23 | Target above or below, using exponential row weights compared with the player's row |
| 24 | Surfacing condition from the gauge |
| 25–27 | Surface-row commands: left, right and dive |
| 28 | Player in row 1 |
| 29 | Player in row 5 or lower, which sets the preferred dodge direction |

**Second layer:** Units 0–2 combine the target and threat signals, with the threat split by dodge direction. Units 3–5 threshold the analog blocked level, and units 6–12 pass the remaining signals through. The logits apply the priorities, with large penalties on blocked moves.

```edits
# ---------- E_r: player in row r and target in row (units 0..6, rows 2..8)
b1[0:7] = -148
W1[120:132:6, 0] = 60
W1[121:133:6, 0] = -32
W1[133:180:6, 0] = 24
W1[122:140:6, 0] = 32
W1[140:180:6, 0] = 8
W1[130, 0] = -16
W1[180:192:6, 1] = 60
W1[181:193:6, 1] = -32
W1[193:240:6, 1] = 24
W1[182:200:6, 1] = 32
W1[200:240:6, 1] = 8
W1[190, 1] = -16
W1[240:252:6, 2] = 60
W1[241:253:6, 2] = -32
W1[253:300:6, 2] = 24
W1[242:260:6, 2] = 32
W1[260:300:6, 2] = 8
W1[250, 2] = -16
W1[300:312:6, 3] = 60
W1[301:313:6, 3] = -32
W1[313:360:6, 3] = 24
W1[302:320:6, 3] = 32
W1[320:360:6, 3] = 8
W1[310, 3] = -16
W1[360:372:6, 4] = 60
W1[361:373:6, 4] = -32
W1[373:420:6, 4] = 24
W1[362:380:6, 4] = 32
W1[380:420:6, 4] = 8
W1[370, 4] = -16
W1[420:432:6, 5] = 60
W1[421:433:6, 5] = -32
W1[433:480:6, 5] = 24
W1[422:440:6, 5] = 32
W1[440:480:6, 5] = 8
W1[430, 5] = -16
W1[480:492:6, 6] = 60
W1[481:493:6, 6] = -32
W1[493:540:6, 6] = 24
W1[482:500:6, 6] = 32
W1[500:540:6, 6] = 8
W1[490, 6] = -16

# ---------- X_r: player in row r and immediate threat (units 7..13, rows 2..8)
b1[7:14] = -64
W1[120:132:6, 7] = 30
W1[121, 7] = 8
W1[133:151:6, 7] = 8
W1[134:152:6, 7] = -8
W1[180:192:6, 8] = 30
W1[181, 8] = 8
W1[193:211:6, 8] = 8
W1[194:212:6, 8] = -8
W1[240:252:6, 9] = 30
W1[241, 9] = 8
W1[253:271:6, 9] = 8
W1[254:272:6, 9] = -8
W1[300:312:6, 10] = 30
W1[301, 10] = 8
W1[313:331:6, 10] = 8
W1[314:332:6, 10] = -8
W1[360:372:6, 11] = 30
W1[361, 11] = 8
W1[373:391:6, 11] = 8
W1[374:392:6, 11] = -8
W1[420:432:6, 12] = 30
W1[421, 12] = 8
W1[433:451:6, 12] = 8
W1[434:452:6, 12] = -8
W1[480:492:6, 13] = 30
W1[481, 13] = 8
W1[493:511:6, 13] = 8
W1[494:512:6, 13] = -8

# ---------- B_r: analog blocked level (units 14..21, rows 1..8)
b1[14:22] = -22
W1[60:72:6, 14] = 10
W1[121:139:6, 14] = 1
W1[120:132:6, 15] = 10
W1[61:79:6, 15] = 3
W1[181:199:6, 15] = 1
W1[180:192:6, 16] = 10
W1[121:139:6, 16] = 3
W1[241:259:6, 16] = 1
W1[240:252:6, 17] = 10
W1[181:199:6, 17] = 3
W1[301:319:6, 17] = 1
W1[300:312:6, 18] = 10
W1[241:259:6, 18] = 3
W1[361:379:6, 18] = 1
W1[360:372:6, 19] = 10
W1[301:319:6, 19] = 3
W1[421:439:6, 19] = 1
W1[420:432:6, 20] = 10
W1[361:379:6, 20] = 3
W1[481:499:6, 20] = 1
W1[480:492:6, 21] = 10
W1[421:439:6, 21] = 3

# ---------- U: target above the player (unit 22)
W1[121:133:6, 22] = -32768
W1[133:180:6, 22] = 32768
W1[122:140:6, 22] = 32768
W1[130, 22] = -32768
W1[181:193:6, 22] = -8192
W1[193:240:6, 22] = 8192
W1[182:200:6, 22] = 8192
W1[190, 22] = -8192
W1[241:253:6, 22] = -2048
W1[253:300:6, 22] = 2048
W1[242:260:6, 22] = 2048
W1[250, 22] = -2048
W1[301:313:6, 22] = -512
W1[313:360:6, 22] = 512
W1[302:320:6, 22] = 512
W1[310, 22] = -512
W1[361:373:6, 22] = -128
W1[373:420:6, 22] = 128
W1[362:380:6, 22] = 128
W1[370, 22] = -128
W1[421:433:6, 22] = -32
W1[433:480:6, 22] = 32
W1[422:440:6, 22] = 32
W1[430, 22] = -32
W1[481:493:6, 22] = -8
W1[493:540:6, 22] = 8
W1[482:500:6, 22] = 8
W1[490, 22] = -8
W1[0:60:6, 22] = -458752
W1[60:120:6, 22] = -458752
W1[120, 22] = -114688
W1[180, 22] = -28672
W1[240, 22] = -7168
W1[300, 22] = -1792
W1[360, 22] = -448
W1[420, 22] = -112
W1[480, 22] = -28

# ---------- D: target below the player (unit 23)
W1[121:133:6, 23] = -8
W1[133:180:6, 23] = 8
W1[122:140:6, 23] = 8
W1[130, 23] = -8
W1[181:193:6, 23] = -32
W1[193:240:6, 23] = 32
W1[182:200:6, 23] = 32
W1[190, 23] = -32
W1[241:253:6, 23] = -128
W1[253:300:6, 23] = 128
W1[242:260:6, 23] = 128
W1[250, 23] = -128
W1[301:313:6, 23] = -512
W1[313:360:6, 23] = 512
W1[302:320:6, 23] = 512
W1[310, 23] = -512
W1[361:373:6, 23] = -2048
W1[373:420:6, 23] = 2048
W1[362:380:6, 23] = 2048
W1[370, 23] = -2048
W1[421:433:6, 23] = -8192
W1[433:480:6, 23] = 8192
W1[422:440:6, 23] = 8192
W1[430, 23] = -8192
W1[481:493:6, 23] = -32768
W1[493:540:6, 23] = 32768
W1[482:500:6, 23] = 32768
W1[490, 23] = -32768
W1[0:60:6, 23] = -458752
W1[60:120:6, 23] = -458752
W1[120, 23] = -28
W1[180, 23] = -112
W1[240, 23] = -448
W1[300, 23] = -1792
W1[360, 23] = -7168
W1[420, 23] = -28672
W1[480, 23] = -114688

# ---------- Surfacing condition from the gauge (unit 24)
W1[593, 24] = 12
W1[551, 24] = -12
W1[557, 24] = -12
W1[563, 24] = 12
b1[24] = -6

# ---------- Surface-row alignment and dive (units 25, 26, 27)
W1[12:60:6, 25] = 12
b1[25] = -6
W1[10, 26] = 12
W1[12:60:6, 26] = -30
b1[26] = -6
W1[4, 27] = 12
W1[61:79:6, 27] = -30
b1[27] = -6

# ---------- Player in row 1 (unit 28)
W1[60:120:6, 28] = 12
b1[28] = -6

# ---------- Player in rows 5..8 (unit 29)
W1[300, 29] = 12
W1[360, 29] = 12
W1[420, 29] = 12
W1[480, 29] = 12
b1[29] = -6

# ---------- Second layer
W2[0:7, 0] = 5
b2[0] = 30
W2[7:14, 1] = 5
W2[29, 1] = 5
b2[1] = 25
W2[7:14, 2] = 5
W2[29, 2] = -5
b2[2] = 25
W2[14:22, 3] = 40
b2[3] = 314.52
W2[14:22, 4] = 40
b2[4] = 264.8
W2[14:22, 5] = 40
b2[5] = 245.48
W2[22, 6] = 5
W2[23, 7] = 5
W2[24, 8] = 5
W2[25, 9] = 5
W2[26, 10] = 5
W2[27, 11] = 5
W2[28, 12] = 5

# ---------- Logits: 0 no-op, 1 left, 2 up, 3 right, 4 down, 5 fire
W3[0, 5] = 50
W3[1, 2] = 60
W3[1, 4] = 55
W3[2, 2] = 55
W3[2, 4] = 60
W3[3, 4] = -200
W3[4, 2] = -200
W3[4, 4] = 200
W3[5, 4] = -200
W3[6, 2] = 37.5
W3[7, 4] = 42.5
W3[8, 2] = 100
W3[9, 1] = 75
W3[10, 3] = 75
W3[11, 4] = 75
W3[12, 4] = 75
b3[0] = 10
b3[1] = 25
b3[2] = 2.5
b3[3] = 25
b3[4] = 57.5
b3[5] = 0
```