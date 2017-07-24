# DeepMind Mini Games

## MoveToBeacon

#### Description

A map with 1 Marine and 1 Beacon. Rewards are earned by moving the marine to the
beacon. Whenever the Marine earns a reward for reaching the Beacon, the Beacon
is teleported to a random location (at least 5 units away from Marine).

#### Initial State

*   1 Marine at random location (unselected)
*   1 Beacon at random location (at least 4 units away from Marine)

#### Rewards

*   Marine reaches Beacon: +1

#### End Condition

*   Time elapsed

#### Time Limit

*   120 seconds

#### Additional Notes

*   Fog of War disabled
*   No camera movement required (single-screen)

## CollectMineralShards

#### Description

A map with 2 Marines and an endless supply of Mineral Shards. Rewards are earned
by moving the Marines to collect the Mineral Shards, with optimal collection
requiring both Marine units to be split up and moved independently. Whenever all
20 Mineral Shards have been collected, a new set of 20 Mineral Shards are
spawned at random locations (at least 2 units away from all Marines).

#### Initial State

*   2 Marines at random locations (unselected)
*   20 Mineral Shards at random locations (at least 2 units away from all
    Marines)

#### Rewards

*   Marine collects Mineral Shard: +1

#### End Condition

*   Time elapsed

#### Time Limit

*   120 seconds

#### Additional Notes

*   Fog of War disabled
*   No camera movement required (single-screen)
*   This is the only map in the set to require the Liberty (Campaign) mod, which
    is needed for the Mineral Shard unit.

## FindAndDefeatZerglings

#### Description

A map with 3 Marines and an endless supply of stationary Zerglings. Rewards are
earned by using the Marines to defeat Zerglings, with the optimal strategy
requiring a combination of efficient exploration and combat. Whenever all 25
Zerglings have been defeated, a new set of 25 Zerglings are spawned at random
locations (at least 9 units away from all Marines and at least 5 units away from
all other Zerglings).

#### Initial State

*   3 Marines at map center (preselected)
*   2 Zerglings spawned at random locations inside player's vision range
    (between 7.5 and 9.5 units away from map center and at least 5 units away
    from all other Zerglings)
*   23 Zerglings spawned at random locations outside player's vision range (at
    least 10.5 units away from map center and at least 5 units away from all
    other Zerglings)

#### Rewards

*   Zergling defeated: +1
*   Marine defeated: -1

#### End Conditions

*   Time elapsed
*   All Marines defeated

#### Time Limit

*   180 seconds

#### Additional Notes

*   Fog of War enabled
*   Camera movement required (map is larger than single-screen)

## DefeatRoaches

#### Description

A map with 9 Marines and a group of 4 Roaches on opposite sides. Rewards are
earned by using the Marines to defeat Roaches, with optimal combat strategy
requiring the Marines to perform focus fire on the Roaches. Whenever all 4
Roaches have been defeated, a new group of 4 Roaches is spawned and the player
is awarded 5 additional Marines at full health, with all other surviving Marines
retaining their existing health (no restore). Whenever new units are spawned,
all unit positions are reset to opposite sides of the map.

#### Initial State

*   9 Marines in a vertical line at a random side of the map (preselected)
*   4 Roaches in a vertical line at the opposite side of the map from the
    Marines

#### Rewards

*   Roach defeated: +10
*   Marine defeated: -1

#### End Conditions

*   Time elapsed
*   All Marines defeated

#### Time Limit

*   120 seconds

#### Additional Notes

*   Fog of War disabled
*   No camera movement required (single-screen)
*   This map and DefeatZerglingsAndBanelings are currently the only maps in the
    set that can include an automatic, mid-episode state change for
    player-controlled units. The Marine units are automatically moved back to a
    neutral position (at a random side of the map opposite the Roaches) when new
    units are spawned, which occurs whenever the current set of Roaches is
    defeated. This is done in order to guarantee that new units do not spawn
    within combat range of one another.

## DefeatZerglingsAndBanelings

#### Description

A map with 9 Marines on the opposite side from a group of 6 Zerglings and 4
Banelings. Rewards are earned by using the Marines to defeat Zerglings and
Banelings. Whenever all Zerglings and Banelings have been defeated, a new group
of 6 Zerglings and 4 Banelings is spawned and the player is awarded 4 additional
Marines at full health, with all other surviving Marines retaining their
existing health (no restore). Whenever new units are spawned, all unit positions
are reset to opposite sides of the map.

#### Initial State

*   9 Marines in a vertical line at a random side of the map (preselected)
*   6 Zerglings and 4 Banelings in a group at the opposite side of the map from
    the Marines

#### Rewards

*   Zergling defeated: +5
*   Baneling defeated: +5
*   Marine defeated: -1

#### End Conditions

*   Time elapsed
*   All Marines defeated

#### Time Limit

*   120 seconds

#### Additional Notes

*   Fog of War disabled
*   No camera movement required (single-screen)
*   This map and DefeatRoaches are currently the only maps in the set that can
    include an automatic, mid-episode state change for player-controlled units.
    The Marine units are automatically moved back to a neutral position (at a
    random side of the map opposite the Roaches) when new units are spawned,
    which occurs whenever the current set of Zerglings and Banelings is
    defeated. This is done in order to guarantee that new units do not spawn
    within combat range of one another.

## CollectMineralsAndGas

#### Description

A map with 12 SCVs, 1 Command Center, 16 Mineral Fields and 4 Vespene Geysers.
Rewards are based on the total amount of Minerals and Vespene Gas collected.
Spending Minerals and Vespene Gas to train new units does not decrease your
reward tally. Optimal collection will require expanding your capacity to gather
Minerals and Vespene Gas by constructing additional SCVs and an additional
Command Center.

#### Initial State

*   12 SCVs beside the Command Center (unselected)
*   1 Command Center at a fixed location
*   16 Mineral Fields at fixed locations
*   4 Vespene Geysers at fixed locations
*   Player Resources: 50 Minerals, 0 Vespene, 12/15 Supply

#### Rewards

Reward total is equal to the total amount of Minerals and Vespene Gas collected

#### End Condition

Time elapsed

#### Time Limit

300 seconds

## BuildMarines

#### Description

A map with 12 SCVs, 1 Command Center, and 8 Mineral Fields. Rewards are earned
by building Marines. This is accomplished by using SCVs to collect minerals,
which are used to build Supply Depots and Barracks, which can then build
Marines.

#### Initial State

*   12 SCVs beside the Command Center (unselected)
*   1 Command Center at a fixed location
*   8 Mineral Fields at fixed locations
*   Player Resources: 50 Minerals, 0 Vespene, 12/15 Supply

#### Rewards

Reward total is equal to the total number of Marines built

#### End Condition

Time elapsed

#### Time Limit

900 seconds

#### Additional Notes

*   Fog of War disabled
*   No camera movement required (single-screen)
*   This is the only map in the set that explicitly limits the available actions
    of the units to disallow actions which are not pertinent to the goal of the
    map. Actions that are not required for building Marines have been removed.
