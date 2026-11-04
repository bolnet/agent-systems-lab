I use a fixed-column, left-facing strategy: fire while waiting, move vertically to intercept approaching divers, and surface with a diver when oxygen falls below 60. Keeping horizontal actions disabled preserves the submarine geometry used by the detectors.

The first layer computes row-wise diver desirability, direction estimates from trails, nearby hazards, player position, and the surfacing condition. The second layer combines these into vertical pursuit, firing holds, collision avoidance, and boundary guards. Stronger avoidance weights take precedence over ordinary pursuit. This is a hand-designed heuristic, not a claim of verified optimality.

```edits
# First-layer biases.
b1[0:8] = -4.5
b1[8:24] = -48.55
b1[25:27] = -5
b1[27] = -6
b1[28] = -5
b1[29:32] = -51

# Units 0..7: approaching-diver desirability in rows 1..8.
# Reward minus danger separates divers from enemies.
# Negative trail weights favor trajectories approaching column 5.
# Player weights compensate for the submarine's own back-cell trail.
W1[60:120:6, 0] = 3
W1[61:120:6, 0] = [-2.25, -3, -4.5, -6.75, -9.75, -13.5, -9.75, -6.75, -4.5, -3]
W1[62:120:6, 0] = [2.25, 3, 4.5, 6.75, 9.75, 13.5, 9.75, 6.75, 4.5, 3]
W1[64:120:6, 0] = [0, 0, -0.75, -3, -6, -9, -6, -3, -0.75, 0]

W1[120:180:6, 1] = 3
W1[121:180:6, 1] = [-2.25, -3, -4.5, -6.75, -9.75, -13.5, -9.75, -6.75, -4.5, -3]
W1[122:180:6, 1] = [2.25, 3, 4.5, 6.75, 9.75, 13.5, 9.75, 6.75, 4.5, 3]
W1[124:180:6, 1] = [0, 0, -0.75, -3, -6, -9, -6, -3, -0.75, 0]

W1[180:240:6, 2] = 3
W1[181:240:6, 2] = [-2.25, -3, -4.5, -6.75, -9.75, -13.5, -9.75, -6.75, -4.5, -3]
W1[182:240:6, 2] = [2.25, 3, 4.5, 6.75, 9.75, 13.5, 9.75, 6.75, 4.5, 3]
W1[184:240:6, 2] = [0, 0, -0.75, -3, -6, -9, -6, -3, -0.75, 0]

W1[240:300:6, 3] = 3
W1[241:300:6, 3] = [-2.25, -3, -4.5, -6.75, -9.75, -13.5, -9.75, -6.75, -4.5, -3]
W1[242:300:6, 3] = [2.25, 3, 4.5, 6.75, 9.75, 13.5, 9.75, 6.75, 4.5, 3]
W1[244:300:6, 3] = [0, 0, -0.75, -3, -6, -9, -6, -3, -0.75, 0]

W1[300:360:6, 4] = 3
W1[301:360:6, 4] = [-2.25, -3, -4.5, -6.75, -9.75, -13.5, -9.75, -6.75, -4.5, -3]
W1[302:360:6, 4] = [2.25, 3, 4.5, 6.75, 9.75, 13.5, 9.75, 6.75, 4.5, 3]
W1[304:360:6, 4] = [0, 0, -0.75, -3, -6, -9, -6, -3, -0.75, 0]

W1[360:420:6, 5] = 3
W1[361:420:6, 5] = [-2.25, -3, -4.5, -6.75, -9.75, -13.5, -9.75, -6.75, -4.5, -3]
W1[362:420:6, 5] = [2.25, 3, 4.5, 6.75, 9.75, 13.5, 9.75, 6.75, 4.5, 3]
W1[364:420:6, 5] = [0, 0, -0.75, -3, -6, -9, -6, -3, -0.75, 0]

W1[420:480:6, 6] = 3
W1[421:480:6, 6] = [-2.25, -3, -4.5, -6.75, -9.75, -13.5, -9.75, -6.75, -4.5, -3]
W1[422:480:6, 6] = [2.25, 3, 4.5, 6.75, 9.75, 13.5, 9.75, 6.75, 4.5, 3]
W1[424:480:6, 6] = [0, 0, -0.75, -3, -6, -9, -6, -3, -0.75, 0]

W1[480:540:6, 7] = 3
W1[481:540:6, 7] = [-2.25, -3, -4.5, -6.75, -9.75, -13.5, -9.75, -6.75, -4.5, -3]
W1[482:540:6, 7] = [2.25, 3, 4.5, 6.75, 9.75, 13.5, 9.75, 6.75, 4.5, 3]
W1[484:540:6, 7] = [0, 0, -0.75, -3, -6, -9, -6, -3, -0.75, 0]

# Units 8..15: hazards in the current row or the row above.
# Small far-left contributions encourage holding position and firing.
W1[60:120:6, 8] = 24
W1[120:180:6, 8] = 20.025
W1[61:80:6, 8] = 0.18
W1[85:98:6, 8] = 8

W1[120:180:6, 9] = 24
W1[180:240:6, 9] = 20.025
W1[121:140:6, 9] = 0.18
W1[145:158:6, 9] = 8

W1[180:240:6, 10] = 24
W1[240:300:6, 10] = 20.025
W1[181:200:6, 10] = 0.18
W1[205:218:6, 10] = 8

W1[240:300:6, 11] = 24
W1[300:360:6, 11] = 20.025
W1[241:260:6, 11] = 0.18
W1[265:278:6, 11] = 8

W1[300:360:6, 12] = 24
W1[360:420:6, 12] = 20.025
W1[301:320:6, 12] = 0.18
W1[325:338:6, 12] = 8

W1[360:420:6, 13] = 24
W1[420:480:6, 13] = 20.025
W1[361:380:6, 13] = 0.18
W1[385:398:6, 13] = 8

W1[420:480:6, 14] = 24
W1[480:540:6, 14] = 20.025
W1[421:440:6, 14] = 0.18
W1[445:458:6, 14] = 8

W1[480:540:6, 15] = 24
W1[481:500:6, 15] = 0.18
W1[505:518:6, 15] = 8

# Units 16..23: hazards in the current row or the row below.
W1[60:120:6, 16] = 24
W1[0:60:6, 16] = 20.025
W1[61:80:6, 16] = 0.18
W1[85:98:6, 16] = 8

W1[120:180:6, 17] = 24
W1[60:120:6, 17] = 20.025
W1[121:140:6, 17] = 0.18
W1[145:158:6, 17] = 8

W1[180:240:6, 18] = 24
W1[120:180:6, 18] = 20.025
W1[181:200:6, 18] = 0.18
W1[205:218:6, 18] = 8

W1[240:300:6, 19] = 24
W1[180:240:6, 19] = 20.025
W1[241:260:6, 19] = 0.18
W1[265:278:6, 19] = 8

W1[300:360:6, 20] = 24
W1[240:300:6, 20] = 20.025
W1[301:320:6, 20] = 0.18
W1[325:338:6, 20] = 8

W1[360:420:6, 21] = 24
W1[300:360:6, 21] = 20.025
W1[361:380:6, 21] = 0.18
W1[385:398:6, 21] = 8

W1[420:480:6, 22] = 24
W1[360:420:6, 22] = 20.025
W1[421:440:6, 22] = 0.18
W1[445:458:6, 22] = 8

W1[480:540:6, 23] = 24
W1[420:480:6, 23] = 20.025
W1[481:500:6, 23] = 0.18
W1[505:518:6, 23] = 8

# Unit 24: approximately 0.01 times player row.
W1[60:120:6, 24] = 0.005
W1[120:180:6, 24] = 0.01
W1[180:240:6, 24] = 0.015
W1[240:300:6, 24] = 0.02
W1[300:360:6, 24] = 0.025
W1[360:420:6, 24] = 0.03
W1[420:480:6, 24] = 0.035
W1[480:540:6, 24] = 0.04

# Units 25, 26, 28: surface, row 1, and bottom-row indicators.
W1[0:60:6, 25] = 5
W1[60:120:6, 26] = 5
W1[480:540:6, 28] = 5

# Unit 27: oxygen below 60 AND at least one diver.
# At this oxygen level, gauge column 8 unambiguously indicates divers.
W1[557, 27] = -24
W1[593, 27] = 12

# Units 29..31: additional firing opportunities in rows 1..3.
W1[60:120:6, 29] = 24
W1[61:80:6, 29] = 6
W1[120:180:6, 30] = 24
W1[121:140:6, 30] = 6
W1[180:240:6, 31] = 24
W1[181:200:6, 31] = 6

# Second-layer units 0..7: pursue divers above.
W2[0, 0] = 20
W2[1, 1] = 20
W2[2, 2] = 20
W2[3, 3] = 20
W2[4, 4] = 20
W2[5, 5] = 20
W2[6, 6] = 20
W2[7, 7] = 20
W2[24, 0:8] = 400
b2[0:8] = [-46, -50, -54, -58, -62, -66, -70, -74]

# Second-layer units 8..15: pursue divers below.
W2[0, 8] = 20
W2[1, 9] = 20
W2[2, 10] = 20
W2[3, 11] = 20
W2[4, 12] = 20
W2[5, 13] = 20
W2[6, 14] = 20
W2[7, 15] = 20
W2[24, 8:16] = -400
b2[8:16] = [-38, -34, -30, -26, -22, -18, -14, -10]

# Disable ordinary pursuit during an oxygen return.
W2[27, 0:16] = -20

# Units 16 and 17: upward and downward movement penalties.
W2[8:16, 16] = 0.1
W2[16:24, 17] = 0.1
W2[25, 16:18] = 0.025
b2[16:18] = 0.775

# Unit 18: strong current-row hazard; stop holding position.
W2[8:24, 18] = 5
b2[18] = 62.5

# Unit 19: oxygen-return drive.
W2[27, 19] = 3

# Unit 20: leave the surface.
W2[25, 20] = 3

# Unit 21: forbid premature surfacing from row 1.
W2[26, 21] = 4
W2[27, 21] = -4
b2[21] = -4

# Units 22..29: hold the row of an approaching diver.
W2[0, 22] = 6
W2[8, 22] = 10
W2[16, 22] = 10

W2[1, 23] = 6
W2[9, 23] = 10
W2[17, 23] = 10

W2[2, 24] = 6
W2[10, 24] = 10
W2[18, 24] = 10

W2[3, 25] = 6
W2[11, 25] = 10
W2[19, 25] = 10

W2[4, 26] = 6
W2[12, 26] = 10
W2[20, 26] = 10

W2[5, 27] = 6
W2[13, 27] = 10
W2[21, 27] = 10

W2[6, 28] = 6
W2[14, 28] = 10
W2[22, 28] = 10

W2[7, 29] = 6
W2[15, 29] = 10
W2[23, 29] = 10
b2[22:30] = 7

# Unit 30: bottom boundary.
W2[28, 30] = 3

# Unit 31: shooting hold, disabled during oxygen return.
W2[29:32, 31] = 3
W2[27, 31] = -8
b2[31] = -2

# Output baselines: fire is the default waiting action.
# Horizontal actions are suppressed to preserve column and orientation.
b3[0:6] = [-1000, -1000, -40, -1000, -45.5, -18.05]

# Slight preference for shallower diver targets breaks pursuit ties.
W3[0:8, 2] = [9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5]
W3[8:16, 4] = [9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5]

# Collision avoidance.
W3[16, 2] = -1000
W3[17, 4] = -1000
W3[18, 5] = -130

# Oxygen return and boundary management.
W3[19, 2] = 22
W3[20, 4] = 16
W3[21, 2] = -120
W3[30, 4] = -120

# Hold position and shoot while intercepting divers or engaging enemies.
W3[22:30, 5] = 12
W3[31, 5] = 10
```