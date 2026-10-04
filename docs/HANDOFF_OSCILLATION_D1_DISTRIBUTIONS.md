# D1 adopted-policy distributions

Counts are exact; histograms show `value: count`. Windows include the action at clear and the endpoint. Partial windows stop at match end; they are explicitly separated from complete 10/20/30 s exposure. Recovery after re-entry remains included in window totals. Censored episodes are never counted as stable successes.

## 142 (100 matches)

Clears: 37. Before/at clear: (33, 35): 37.

| Horizon s | Re-entry | Survived through | Censored | Episode rate | Match rapid/admissible |
|---:|---:|---:|---:|---:|---:|
| 5 | 0 | 32 | 5 | 0/32 = 0.000000 | 0/32 |
| 10 | 30 | 2 | 5 | 30/32 = 0.937500 | 30/32 |
| 15 | 30 | 0 | 7 | 30/30 = 1.000000 | 30/30 |
| 20 | 30 | 0 | 7 | 30/30 = 1.000000 | 30/30 |
| 30 | 30 | 0 | 7 | 30/30 = 1.000000 | 30/30 |

Clear times (all): 140: 1, 150: 1, 180: 1, 190: 2, 200: 2, 210: 3, 220: 2, 230: 5, 240: 2, 250: 2, 260: 2, 270: 5, 280: 4, 290: 2, 300: 3.

First-clear times: 140: 1, 150: 1, 180: 1, 190: 2, 200: 2, 210: 3, 220: 2, 230: 5, 240: 2, 250: 2, 260: 2, 270: 5, 280: 4, 290: 2, 300: 3. Median 240 s.

Clear cycles per match: 0: 63, 1: 37.

Re-entry cycles per match: 0: 7, 1: 30 (among clear matches).

First action: mount.bottom.bridge: 23, mount.bottom.elbow_knee_escape: 2, mount.bottom.trap_and_roll_escape: 9, timeout: 3.

First spend delay: 0: 34, censored: 3.

Re-entry delay: 10: 30, censored: 7.

10 s complete windows (n=32): spend 16: 30, 9: 2; recovery 0: 32.

10 s partial/censored windows (n=5): spend 0: 3, 7: 2; recovery 0: 5.

20 s complete windows (n=19): spend 16: 2, 19: 17; recovery 4: 19.

20 s partial/censored windows (n=18): spend 0: 3, 16: 11, 7: 2, 9: 2; recovery 0: 18.

30 s complete windows (n=16): spend 19: 4, 22: 12; recovery 8: 16.

30 s partial/censored windows (n=21): spend 0: 3, 16: 13, 19: 1, 7: 2, 9: 2; recovery 0: 18, 4: 3.

## 42 (100 matches)

Clears: 46. Before/at clear: (33, 35): 46.

| Horizon s | Re-entry | Survived through | Censored | Episode rate | Match rapid/admissible |
|---:|---:|---:|---:|---:|---:|
| 5 | 0 | 37 | 9 | 0/37 = 0.000000 | 0/36 |
| 10 | 34 | 3 | 9 | 34/37 = 0.918919 | 33/36 |
| 15 | 34 | 0 | 12 | 34/34 = 1.000000 | 33/33 |
| 20 | 34 | 0 | 12 | 34/34 = 1.000000 | 33/33 |
| 30 | 34 | 0 | 12 | 34/34 = 1.000000 | 33/33 |

Clear times (all): 140: 1, 170: 2, 180: 5, 190: 3, 200: 1, 210: 3, 220: 5, 230: 2, 240: 1, 250: 3, 260: 4, 270: 4, 280: 1, 290: 3, 300: 8.

First-clear times: 140: 1, 170: 2, 180: 5, 190: 3, 200: 1, 210: 3, 220: 5, 230: 2, 240: 1, 250: 3, 260: 4, 270: 4, 290: 3, 300: 8. Median 240 s.

Clear cycles per match: 0: 55, 1: 44, 2: 1.

Re-entry cycles per match: 0: 12, 1: 32, 2: 1 (among clear matches).

First action: mount.bottom.bridge: 28, mount.bottom.elbow_knee_escape: 2, mount.bottom.trap_and_roll_escape: 8, timeout: 8.

First spend delay: 0: 38, censored: 8.

Re-entry delay: 10: 34, censored: 12.

10 s complete windows (n=37): spend 16: 34, 9: 3; recovery 0: 37.

10 s partial/censored windows (n=9): spend 0: 8, 7: 1; recovery 0: 9.

20 s complete windows (n=25): spend 19: 25; recovery 4: 25.

20 s partial/censored windows (n=21): spend 0: 8, 16: 9, 7: 1, 9: 3; recovery 0: 21.

30 s complete windows (n=22): spend 19: 3, 22: 19; recovery 8: 22.

30 s partial/censored windows (n=24): spend 0: 8, 16: 9, 19: 3, 7: 1, 9: 3; recovery 0: 21, 4: 3.

## pooled (200 matches)

Clears: 83. Before/at clear: (33, 35): 83.

| Horizon s | Re-entry | Survived through | Censored | Episode rate | Match rapid/admissible |
|---:|---:|---:|---:|---:|---:|
| 5 | 0 | 69 | 14 | 0/69 = 0.000000 | 0/68 |
| 10 | 64 | 5 | 14 | 64/69 = 0.927536 | 63/68 |
| 15 | 64 | 0 | 19 | 64/64 = 1.000000 | 63/63 |
| 20 | 64 | 0 | 19 | 64/64 = 1.000000 | 63/63 |
| 30 | 64 | 0 | 19 | 64/64 = 1.000000 | 63/63 |

Clear times (all): 140: 2, 150: 1, 170: 2, 180: 6, 190: 5, 200: 3, 210: 6, 220: 7, 230: 7, 240: 3, 250: 5, 260: 6, 270: 9, 280: 5, 290: 5, 300: 11.

First-clear times: 140: 2, 150: 1, 170: 2, 180: 6, 190: 5, 200: 3, 210: 6, 220: 7, 230: 7, 240: 3, 250: 5, 260: 6, 270: 9, 280: 4, 290: 5, 300: 11. Median 240.0 s.

Clear cycles per match: 0: 118, 1: 81, 2: 1.

Re-entry cycles per match: 0: 19, 1: 62, 2: 1 (among clear matches).

First action: mount.bottom.bridge: 51, mount.bottom.elbow_knee_escape: 4, mount.bottom.trap_and_roll_escape: 17, timeout: 11.

First spend delay: 0: 72, censored: 11.

Re-entry delay: 10: 64, censored: 19.

10 s complete windows (n=69): spend 16: 64, 9: 5; recovery 0: 69.

10 s partial/censored windows (n=14): spend 0: 11, 7: 3; recovery 0: 14.

20 s complete windows (n=44): spend 16: 2, 19: 42; recovery 4: 44.

20 s partial/censored windows (n=39): spend 0: 11, 16: 20, 7: 3, 9: 5; recovery 0: 39.

30 s complete windows (n=38): spend 19: 7, 22: 31; recovery 8: 38.

30 s partial/censored windows (n=45): spend 0: 11, 16: 22, 19: 4, 7: 3, 9: 5; recovery 0: 39, 4: 6.
