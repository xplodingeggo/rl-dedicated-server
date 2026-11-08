"""Game settings (mutators) and the game tags they write, as Rocket Plugin lists them.
The first option of each setting is the default and writes no tag.
"""

BOTS = ["BotsNone", "BotsEasy", "BotsMedium", "BotsHard", "BotsUnfair"]

# Game modes: shown name and the game class the server runs (`game=` URL option). Soccar is the default.
MODES = [
    ('Soccar', 'GameInfo_Soccar_TA'),
    ('Hoops', 'GameInfo_Basketball_TA'),
    ('Snow Day', 'GameInfo_Hockey_TA'),
    ('Dropshot', 'GameInfo_Breakout_TA'),
    ('Heatseeker', 'GameInfo_GodBall_TA'),
    ('Heatseeker Territory', 'GameInfo_HeatseekerTerritory_TA'),
    ('Snow Day Territory', 'GameInfo_SnowDayTerritory_TA'),
    ('Knockout', 'GameInfo_KnockOut_TA'),
    ('Gridiron', 'GameInfo_Football_TA'),
    ('Spike Rush', 'GameInfo_SpikeDrop_TA'),
    ('Magnus Futball', 'GameInfo_MagnusFutball_TA'),
]

SETTINGS = [
    ('Match Length', [
        ('5 Minutes', ''),
        ('10 Minutes', '10Minutes'),
        ('20 Minutes', '20Minutes'),
        ('Unlimited', 'UnlimitedTime'),
    ]),
    ('Max Score', [
        ('Default', ''),
        ('1 Goal', 'Max1'),
        ('3 Goals', 'Max3'),
        ('5 Goals', 'Max5'),
        ('7 Goals', 'Max7'),
        ('Unlimited', 'UnlimitedScore'),
    ]),
    ('Overtime', [
        ('Unlimited', ''),
        ('+5 Max, First Score', 'Overtime5MinutesFirstScore'),
        ('+5 Max, Random Team', 'Overtime5MinutesRandom'),
    ]),
    ('Max Time Limit', [
        ('Default', ''),
        ('11 Minutes', 'MaxTime11Minutes'),
    ]),
    ('Series Length', [
        ('Unlimited', ''),
        ('3 Games', '3Games'),
        ('5 Games', '5Games'),
        ('7 Games', '7Games'),
    ]),
    ('Game Speed', [
        ('Default', ''),
        ('Slo-mo', 'SloMoGameSpeed'),
        ('Time Warp', 'SloMoDistanceBall'),
    ]),
    ('Ball Max Speed', [
        ('Default', ''),
        ('Slow', 'SlowBall'),
        ('Fast', 'FastBall'),
        ('Super Fast', 'SuperFastBall'),
    ]),
    ('Ball Type', [
        ('Default', ''),
        ('Cube', 'Ball_CubeBall'),
        ('Puck', 'Ball_Puck'),
        ('BasketBall', 'Ball_BasketBall'),
        ('BeachBall', 'Ball_BeachBall'),
        ('Anniversary', 'Ball_Anniversary'),
        ('HauntedBall', 'Ball_Haunted'),
    ]),
    ('Ball Gravity', [
        ('Default', ''),
        ('Low', 'LowGravityBall'),
        ('High', 'HighGravityBall'),
        ('Super High', 'SuperGravityBall'),
    ]),
    ('Ball Physics', [
        ('Default', ''),
        ('Light', 'LightBall'),
        ('Heavy', 'HeavyBall'),
        ('Super Light', 'SuperLightBall'),
        ('CurveBall', 'MagnusBall'),
        ('Beach Ball Curve', 'MagnusBeachBall'),
    ]),
    ('Ball Size', [
        ('Default', ''),
        ('Small', 'SmallBall'),
        ('Medium', 'MediumBall'),
        ('Large', 'BigBall'),
        ('Gigantic', 'GiantBall'),
    ]),
    ('Ball Bounciness', [
        ('Default', ''),
        ('Low', 'LowBounciness'),
        ('High', 'HighBounciness'),
        ('Super High', 'SuperBounciness'),
    ]),
    ('Number Of Balls', [
        ('One', ''),
        ('Two', 'TwoBalls'),
        ('Four', 'FourBalls'),
        ('Six', 'SixBalls'),
    ]),
    ('Boosts Amount', [
        ('Default', ''),
        ('No Boost', 'NoBooster'),
        ('Unlimited', 'UnlimitedBooster'),
        ('Recharge (slow)', 'SlowRecharge'),
        ('Recharge (fast)', 'RapidRecharge'),
    ]),
    ('Rumble', [
        ('None', ''),
        ('Default', 'ItemsMode'),
        ('Slow', 'ItemsModeSlow'),
        ('Civilized', 'ItemsModeBallManipulators'),
        ('Destruction Derby', 'ItemsModeCarManipulators'),
        ('Spring Loaded', 'ItemsModeSprings'),
        ('Spikes Only', 'ItemsModeSpikes'),
        ('Rugby', 'ItemsModeRugby'),
        ('Haunted Ball Beam', 'ItemsModeHauntedBallBeam'),
        ('Tactical Rumble', 'ItemsModeSelection'),
    ]),
    ('Boost Strength', [
        ('1X', ''),
        ('1.5X', 'BoostMultiplier1_5x'),
        ('2X', 'BoostMultiplier2x'),
        ('10X', 'BoostMultiplier10x'),
    ]),
    ('Gravity', [
        ('Default', ''),
        ('Low', 'LowGravity'),
        ('High', 'HighGravity'),
        ('Super High', 'SuperGravity'),
        ('Reverse', 'ReverseGravity'),
    ]),
    ('Demolish', [
        ('Default', ''),
        ('Disabled', 'NoDemolish'),
        ('Friendly Fire', 'DemolishAll'),
        ('On Contact', 'AlwaysDemolishOpposing'),
        ('On Contact (FF)', 'AlwaysDemolish'),
    ]),
    ('Respawn Time', [
        ('3 Seconds', ''),
        ('2 Seconds', 'TwoSecondsRespawn'),
        ('1 Second', 'OneSecondsRespawn'),
        ('Disable Goal Reset', 'DisableGoalDelay'),
    ]),
    ('Bot Loadouts', [
        ('Default', ''),
        ('Random', 'RandomizedBotLoadouts'),
    ]),
    ('Audio', [
        ('Default', ''),
        ('Haunted', 'HauntedAudio'),
    ]),
    ('Game Event', [
        ('Default', ''),
        ('Haunted', 'HauntedGameEventRules'),
        ('Rugby', 'RugbyGameEventRules'),
    ]),
]
