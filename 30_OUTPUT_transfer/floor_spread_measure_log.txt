==========================================================================
 floor_spread_measure.py  v1.1   [production -- 20_CODE]
 run 2026-10-21 21:41:59   python 3.14.3
 source C:\Users\thoma\Desktop\xNPV\10_SOURCE  (via SOURCE_DIR from the environment/.env)
==========================================================================
  [age] xnpv1_birthdates.csv: 3204 keys on a pre-built pkey
  production age table: birthdate on 99.94% of season rows (C:\Users\thoma\Desktop\xNPV\30_OUTPUT\WAR_with_age.csv)
skater_forecast v2.4; the dict in force: {0: 0.6767, 1: 0.7545, 2: 0.8026, 3: 0.8499, 4: 0.877, 5: 0.8981}
  page 2015: 958 players
  page 2016: 982 players
  page 2017: 997 players
  page 2018: 1,001 players
  page 2019: 998 players
  page 2020: 994 players
  page 2021: 986 players

guard: start 1.1506, whole 1.3569, rows 40,510 (the build: 1.1506, 1.3587, 40,510)
  rows PASS; gp-weighted RMSE per 82 against the February 1 build: start +0.0000, whole -0.0018

WAR if he plays, mean absolute miss on seasons played, by season ahead (old -> new):
  +0: 0.6767 -> 0.6766   (4,907 seasons played)
  +1: 0.7545 -> 0.7545   (4,354 seasons played)
  +2: 0.8026 -> 0.8023   (3,864 seasons played)
  +3: 0.8499 -> 0.8494   (3,435 seasons played)
  +4: 0.8770 -> 0.8765   (3,048 seasons played)
  +5: 0.8981 -> 0.8975   (2,274 seasons played)

to lock, in skater_forecast.py:
    WAR_IF_PLAYS_MAE = {0: 0.6766, 1: 0.7545, 2: 0.8023, 3: 0.8494, 4: 0.8765, 5: 0.8975}
