## StarCraft II

### What is StarCraft II

[StarCraft II](https://en.wikipedia.org/wiki/StarCraft_II:_Legacy_of_the_Void)
is a [Real Time Strategy
(RTS)](https://en.wikipedia.org/wiki/Real-time_strategy) game written by
[Blizzard](http://blizzard.com/). It's the successor to [StarCraft
Broodwar](https://en.wikipedia.org/wiki/StarCraft:_Brood_War), which is one of
the most successful RTS games. StarCraft II is played by millions of people, and
has a [professional league](https://wcs.starcraft2.com/en-us/).

The [goal in StarCraft](http://us.battle.net/sc2/en/game/guide/whats-sc2) is to
build a base, manage an economy, build an army, and destroy your enemies. You
control your base and army from a third person perspective, then multi-task and
micro-manage your units for maximum effect. StarCraft has 3 distinct races:
[Terran](https://www.youtube.com/watch?v=Fmu8PsUDDtQ),
[Protoss](https://www.youtube.com/watch?v=m0g0MpllFCs) and
[Zerg](https://www.youtube.com/watch?v=Lq74R7wWAnQ), which have different units
and strategies.

The game has a single player campaign, though most people play multiplayer on
[Battle.net](http://battle.net/sc2/en/). There are built-in bots, but they are
fairly weak and predictable, and the stronger ones cheat.

There are many resources online for learning about Starcraft, including
[Battle.net](http://battle.net/sc2/en/),
[TeamLiquid](http://wiki.teamliquid.net/starcraft2/StarCraft) and
[Wikia](http://starcraft.wikia.com/wiki/StarCraft_Wiki).

### Versions

Blizzard regularly updates StarCraft II. These updates are roughly monthly, can
introduce new features, and often have minor gameplay and balance changes to
make the races more even. Replays are tied to the specific version they were
generated with.

### Game and Action Speed

Being a real-time strategy game means the game runs in real-time. In reality
though, the simulation updates 16-22 times per second, depending on your [game
speed](http://wiki.teamliquid.net/starcraft2/Game_Speed), and all the
intermediate rendered frames are just interpolated.

#### Game speed

Acting through an API allows you to control the clock. Instead of running at
16-22 steps per second, you can step as fast or as slow as you want, when you
want. This allows you to run much faster than real-time if the agent is capable,
or much slower if the agent needs to pause to spend some time learning. This
also means there is never any lag. The max speed depends on the step_mul/render
frequency, and the scene complexity/unit count. 10x real-time is not uncommon
and can be much higher for simple maps.

#### APM Calculation

The game calculates and reports APM in a non-obvious way. It isn't obvious how
to count the action of moving the camera with edge scrolling, or how many
actions is building a building. Here are the rules of how it's actually counted
by the game.

There are actually two types reported by the game:

*   Actions Per Minute (APM): counts every action.
*   Effective Actions Per Minute (EPM): filters out actions that have no effect
    (eg: redundant selections).

Different actions count as different number of actions:

*   Commands with target = 2 (eg: move, attack, build building)
*   Commands with no target = 1 (eg: stop, train unit, unload cargo)
*   Smart = 1 (right click)
*   Selection and control groups = 1
*   Everything else = 0 (eg: camera movement)

The in game replay UI exposes this with two different time intervals: average
(average over the entire game so far), and current (average over the last 5
seconds). The API only exposes the average APM.

#### APM and fairness

Humans can't do one action per frame. They range from 30-500 actions per minute
(APM), with 30 being a beginner, 60-100 being average, and professionals
being >200 (over 3 per second!). This is trivial compared to what a fast bot is
capable of though. With the [BWAPI](http://bwapi.github.io/) they control units
individually and routinely go over 5000 APM accomplishing things that are
clearly impossible for humans and considered
[unfair](https://youtu.be/IKVFZ28ybQs?t=45s) or even
[broken](https://youtu.be/0EYH-csTttw?t=28s). Even without controlling the units
individually it would be unfair to be able to act much faster with high
precision.

To at least resemble playing fairly it is a good idea to artificially limit the
APM. The easy way is to limit how often the agent gets observations and can make
an action, and limit it to one action per observation. For example you can do
this by only taking every Nth observation, where N is up for debate. A value of
20 is roughly equal to 50 apm while 5 is roughly 200 apm, so that's a reasonable
range to play with. A more sophisticated way is to give the agent every
observation but limit the number of actions that actually have an effect,
forcing it to mainly make no-ops which wouldn't count as actions.

It's probably better to consider all actions as equivalent, including camera
movement, since allowing very fast camera movement could allow agents to cheat.

### Determinism and Randomness

Starcraft II is mostly deterministic, but it does have some randomness mainly
for cosmetic reasons. The two main random elements are weapon speed and update
order.

Weapon randomness is essentially how fast a unit can get its next shot off after
firing and is between -1 to +2 game steps for almost all units. The idea
being that a group of marines may all start firing together, but the minor
random +/- for the next shot will make the group look less robotic and prevent
them from firing in sync forever. This also means a fair matchup (eg 1v1 marine)
will result in a random outcome.

The update order is random and determines the order of events in a given game
loop. For example, if you have two High Templar that cast feedback on each other
on the same game loop, it will be random which one performs the damage first and
wins.

Unit auto-targeting is deterministic, but complicated. It is based on weapon
scan distance, threat and assistance. Units will consider any enemies with
weapon a higher threat than those without, and enemies that can return fire will
be a higher priority than those that can’t return fire. Units that can't return
fire (eg a missile turret vs a marine) but that are attacking an allied unit (eg
a medivac) will trigger a call for help and increase the priority. A healer
raises its priority when it is healing. If two targets have the same priority
the nearest one will be chosen.

These sources of randomness can be removed/mitigated by setting a random seed.
Replays work by saving the game setup including the random seed, as well as the
list of actions by all players, and then playing forward the simulation.

## Actions and Observations

Starcraft II has a very rich action and observation space. The game outputs
both spatial/visual and structured elements. The structured elements are given
because there is a lot of text and numbers which agents aren't expected to learn
to read, especially at low resolution. It's also because it's hard to reverse
replays back to exactly the same visuals that the human saw.

### Observation

#### Spatial/Visual

##### RGB Pixels

This is still work in progress but will be available in the future.

##### Feature layers

Instead of normal RGB pixels, the game exposes feature layers. There are ~20 of
them broken down between the screen and minimap.

The full list is defined in `pysc2.lib.features`.

###### Minimap

The minimap is a low resolution view of the entire map. It gives an overview of
everything going on, but with less detail than the screen.

You can specify the resolution of the minimap. Maps range from
32-256<sup>2</sup>, with common human maps in the 100-256<sup>2</sup> range.
Humans playing at 1080p get a resolution of ~250<sup>2</sup> in the bottom left
corner of their screen.

These are the minimap feature layers:

*   **height_map**: Shows the terrain levels.
*   **visibility**: Which part of the map are hidden, have been seen or are
    currently visible.
*   **creep**: Which parts have zerg creep.
*   **camera**: Which part of the map are visible in the screen layers.
*   **player_id**: Who owns the units, with absolute ids.
*   **player_relative**: Which units are friendly vs hostile. Takes values in
    [0, 4], denoting [background, self, ally, neutral, enemy] units
    respectively.
*   **selected**: Which units are selected.

###### Screen

The screen is a higher resolution view of part of the map.

It is rendered from a top down orthogonal camera, as opposed to a perspective
camera that a human would get in a real game. This makes certain visuals harder
(eg you can't see elevation by size), but it also makes other things easier (eg
units don't change size as they or the camera moves). This also means that the
visible area is a rectangular part of the map, as opposed to the more
trapezoidal shape in the real game. This means there are bits of the map that an
agent can see that humans can't, and vice versa, but it is roughly similar.

A small unit (eg marine or zergling) is ~0.75 game units across. The camera is
24 game units wide. If you specify a screen resolution of 32<sup>2</sup>, that
means a unit will be 1 pixel wide, meaning you have very low accuracy of its
location. If you have a large group of them you may not be able to tell how many
of them you have. A resolution of at least 64<sup>2</sup> is recommended to be
playable.

These are the screen feature layers:

*   **height_map**: Shows the terrain levels.
*   **visibility**: Which part of the map are hidden, have been seen or are
    currently visible.
*   **creep**: Which parts have zerg creep.
*   **power**: Which parts have protoss power, only shows your power.
*   **player_id**: Who owns the units, with absolute ids.
*   **player_relative**: Which units are friendly vs hostile. Takes values in
    [0, 4], denoting [background, self, ally, neutral, enemy] units
    respectively.
*   **unit_type**: A unit type id
*   **selected**: Which units are selected.
*   **hit_points**: How many hit points the unit has.
*   **energy**: How much energy the unit has.
*   **shields**: How much shields the unit has. Only for protoss units.
*   **unit_density**: How many units are in this pixel.
*   **unit_density_aa**: An anti-aliased version of unit_density with a maximum
    of 16 per unit per pixel. This gives you sub-pixel unit location and size.
    For example if a unit is exactly 1 pixel diameter, `unit_density` will show
    it in exactly 1 pixel regardless of where in that pixel it is actually
    centered. `unit_density_aa` will instead tell you how much of each pixel is
    covered by the unit. A unit that is smaller than a pixel and centered in the
    pixel will give a value less than the max. A unit with diameter 1 centered
    near the corner of a pixel will give roughly a quarter of its value to each
    of the 4 pixels it covers. If multiple units cover a pixel their proportion
    of the pixel covered will be summed, up to a max of 256.

#### Structured

The game offers a fair amount of structured data which agents aren't expected
to read from pixels. Instead these are given as tensors with direct semantic
meaning.

##### General player information

A `(11)` tensor showing general information.

*   player_id
*   minerals
*   vespene
*   food used (otherwise known as supply)
*   food cap
*   food used by army
*   food used by workers
*   idle worker count
*   army count
*   warp gate count (for protoss)
*   larva count (for zerg)

##### Control groups

A `(10, 2)` tensor showing the (unit leader type and count) for each of the 10
control groups. The indices in this tensor are referenced by the `control-group`
action.

[Control groups](http://learningsc2.com/tag/control-groups/) are a way to
remember a selection set so that you can recall them easily later.

##### Single Select

A `(7)` tensor showing information about a selected unit.

*   unit type
*   player_relative
*   health
*   shields
*   energy
*   transport slot taken if it's in a transport
*   build progress as a percentage if it's still being built

##### Multi Select

A `(n, 7)` tensor with the same as [single select](#single-select) but for all
`n` selected units. The indices in this tensor are referenced by the
`select_unit` action.

##### Cargo

A `(n, 7)` tensor similar to [single select](#single-select), but for all the
units in a transport. The indices in this tensor are referenced by the `unload`
action.

##### Build Queue

A `(n, 7)` tensor similar to [single select](#single-select), but for all the
units being built by a production building. The indices in this tensor are
referenced by the `build_queue` action.

##### Available Actions

A `(n)` tensor listing all the action ids that are available at the time of this
observation.

### Actions

The SC2 action space is very big. There are hundreds of possible actions, many
of which take a point in either screen or minimap space, and many of which take
an additional modifier. If you were to flatten the action space into a single
dimension, it'd have millions or even billions of possible actions, most of
which aren't valid, and many of which are highly correlated. Therefore, a flat
discrete action space is not very appropriate.

Instead, we created function actions that are rich enough to give
composability, without the complexity of an arbitrary hierarchy. This is based
on the mental model of a C-style function call which can take some arguments of
specific types. The full set of valid types and functions are defined in
`ValidActions` in `pysc2.lib.actions`, and then each observation specifies which of
the available function is valid this frame. Each action is a single
`FunctionCall` in `pysc2.lib.actions` with all its arguments filled.

The full set of types and functions are defined in `pysc2.lib.actions`.
The set of functions is hard coded and limited to just the actions that humans
have taken, as seen by a large number of replays. It lists both general and
specific functions such that the many forms of cancel are exposed as a single
action.

Hard coding the functions means that actions created in custom maps won't be
usable until they are added to `pysc2.lib.actions`.

To see which actions exist run:

```shell
$ python -m pysc2.bin.valid_actions
```

optionally with `--hide_specific`, `--screen_resolution` or
`--minimap_resolution` if you care about the exact values. This prints something
similar to:

```
   0/no_op                       ()
   1/move_camera                 (1/minimap [64, 64])
   2/select_point                (6/select_point_act [4]; 0/screen [84, 84])
   3/select_rect                 (7/select_add [2]; 0/screen [84, 84]; 2/screen2 [84, 84])
   4/select_control_group        (4/control_group_act [5]; 5/control_group_id [10])
   5/select_unit                 (8/select_unit_act [4]; 9/select_unit_id [500])
   6/select_idle_worker          (10/select_worker [4])
   7/select_army                 (7/select_add [2])
   8/select_warp_gates           (7/select_add [2])
   9/select_larva                ()
  10/unload                      (12/unload_id [500])
  11/build_queue                 (11/build_queue_id [10])
  12/Attack_screen               (3/queued [2]; 0/screen [84, 84])
  13/Attack_minimap              (3/queued [2]; 1/minimap [64, 64])
  14/Attack_Attack_screen        (3/queued [2]; 0/screen [84, 84])
  19/Scan_Move_screen            (3/queued [2]; 0/screen [84, 84])
  23/Behavior_CloakOff_quick     (3/queued [2])
  26/Behavior_CloakOn_quick      (3/queued [2])
  42/Build_Barracks_screen       (3/queued [2]; 0/screen [84, 84])
  44/Build_CommandCenter_screen  (3/queued [2]; 0/screen [84, 84])
 220/Effect_Repair_screen        (3/queued [2]; 0/screen [84, 84])
 221/Effect_Repair_autocast      ()
 264/Harvest_Gather_screen       (3/queued [2]; 0/screen [84, 84])
 303/Morph_Lair_quick            (3/queued [2])
 317/Morph_SiegeMode_quick       (3/queued [2])
 322/Morph_Unsiege_quick         (3/queued [2])
 331/Move_screen                 (3/queued [2]; 0/screen [84, 84])
 333/Patrol_screen               (3/queued [2]; 0/screen [84, 84])
 405/Research_Stimpack_quick     (3/queued [2])
 451/Smart_screen                (3/queued [2]; 0/screen [84, 84])
 452/Smart_minimap               (3/queued [2]; 1/minimap [64, 64])
 453/Stop_quick                  (3/queued [2])
 477/Train_Marine_quick          (3/queued [2])
           *** 100s more lines ***
```

This should be read as: `<function id>/<function name>(<type id>/<type name>
[<value size>, *]; *)`.

Some examples:

*   `1/move_camera (1/minimap [64, 64])` is the `move_camera` function (id `1`),
    which takes one argument named `minimap` (id `1`) which requires two ints
    each in the range `[0, 64)` which represent the coordinates on the minimap.
*   `331/Move_screen (3/queued [2]; 0/screen [84, 84])` is the `Move_screen`
    function (id `331`) which takes two arguments: `queued` (id `3`) which is a
    bool and signifies whether this action should happen now or after previous
    actions, and `screen` (id `0`) which takes two ints each in the range `[0,
    84)` which represent a pixel on the screen.

The function names should be unique, stable and meaningful. The function and
type ids are the index into the list of `function_defs` and `types`.

The `types` are a predefined list of argument types that can be used in a
function call. The exact definitions are in `pysc2.lib.actions.TYPES`

Some actions are general. This is visible in actions.py through an extra param
at function construction. It's often exposed in the name as longer versions
being the specific versions. Above you see `Attack_screen` (general),
`Attack_Attack_screen` and `Scan_Move_screen` (specific). For now only
the general actions are exposed through the environment api.

A `Morph` action transform a unit to a different unit, at least according to the
unit_type in the observation. For example `Morph_Lair_quick` morphs a hatchery
to a lair. `Morph_SiegeMode_quick` and `Morph_Unsiege_quick` morphs a siege tank
between tank and siege mode. An `Effect` is a single effect, rarely cancelable.
A `Behavior` can be turned on and off.

Take a look at the `random_agent` for an example of how to consume
`ValidActions` and fill `FunctionCall`s.

## RL Environment

The main SC2 environment is at `pysc2.env.sc2_env`, with the action and observation
space defined in `pysc2.lib.features`.

The most important argument is `map_name`, which is how to find the map.
Find the names by using `pysc2.bin.map_list` or by looking in `pysc2/maps/*.py`.

`screen_size_px` and `minimap_size_px` let you specify the resolution of the
features layers you get in the observations. Higher resolution obviously gives
higher location precision, at the cost of larger observations as well as a
larger action space.

`step_mul` let's you skip observations and actions. For example a `step_mul` of
16 means that the environment gets stepped forward 16 times in between the
actions of the agent (16 steps = 1 second of game time). It is equivalent to
ignoring certain observations and not sending actions on those frames, except it
also speeds up the environment since it doesn't need to render the skipped
frames.

`save_replay_episodes` and `replay_dir` specify how often to save replays and
where to save them.

Currently there is no multiplayer support.

Use the `run_loop.py` to have your agent interact with the environment.

### Environment wrappers

There is one pre-made environment wrapper:

*   `available_actions_printer`: Prints each available action as it is seen.

## Agents

There are a couple basic agents.

*   `random_agent`: Just plays randomly, shows how to make valid moves.
*   `scripted_agent`: These are scripted for a single easy map.
