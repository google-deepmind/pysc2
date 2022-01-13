# Environment converters

## Overview

The SC2 API uses protos to communicate actions to and observations from the
environment. `sc2_env.py` contains code to marshall between these protos and a
more neural network friendly dictionary of numpy arrays, with accompanying
environment specs. During development of AlphaStar this code was translated to
C++, and new features added. This code is now available in PySC2. See
`converter.cc`, `converter.py`, `converted_env.py`, `replay_converter.py`, for
instance.

Converters are instantiated per-agent, per-episode. They are configurable via
the `ConverterSettings` proto; see `converter.proto`. Though they can be used
directly, it is more typical to use them as part of an environment wrapper
(`converted_env.py`), or via the replay conversion code (`replay_converter.py`).

Note that converters don't have to be used from Python. The C++ code is wrapped
using [pybind11](https://github.com/pybind/pybind11), but may also be used
directly.

Note also that, because converters are implemented in C++, changes to them
require compilation. See [this page](bazel.md) for further information.

## Supported platforms

Use of converters requires either [building with Bazel](bazel.md) or use of an
appropriate pre-built wheel. Only Linux is supported at present.

## Raw mode

If raw settings are provided as part of the converter settings the converter
will operate in raw mode. This mode is so called because it provides raw access
to numerical data, with only limited spatial data for the minimap. Actions are
specified directly for units using their tags. There is support for limiting the
data which the agent receives to the view implied by the current camera
position, similar to how humans perceive the game.

### Action spec

name            | shape                            | dtype | min | max                                         | enabled?
--------------- | -------------------------------- | ----- | --- | ------------------------------------------- | --------
function        | ()                               | int32 | 0   | `num_action_types`                          | always
delay           | ()                               | int32 | 1   | 127                                         | always
queued          | ()                               | int32 | 0   | 1                                           | always
repeat          | ()                               | int32 | 0   | 2                                           | `raw.enable_action_repeat`
target_unit_tag | ()                               | int32 | 0   | `raw.max_unit_count` - 1                    | always
unit_tags       | (`raw.max_unit_selection_size`,) | int32 | 0   | `raw.max_unit_count`                        | always
world           | ()                               | int32 | 0   | `raw.resolution.x` * `raw.resolution.y` - 1 | always

### Observation spec

name                           | shape                                       | dtype | min       | max                                         | enabled?
------------------------------ | ------------------------------------------- | ----- | --------- | ------------------------------------------- | --------
action/function                | ()                                          | int32 | 0         | `num_action_types`                          | `supervised`
action/delay                   | ()                                          | int32 | 1         | 127                                         | `supervised`
action/queued                  | ()                                          | int32 | 0         | 1                                           | `supervised`
action/repeat                  | ()                                          | int32 | 0         | 2                                           | `supervised` and `raw.enable_action_repeat`
action/target_unit_tag         | ()                                          | int32 | 1         | `raw.max_unit_count` - 1                    | `supervised`
action/unit_tags               | (`raw.max_unit_selection_size`,)            | int32 | 0         | `raw.max_unit_count`                        | `supervised`
action/world                   | ()                                          | int32 | 0         | `raw.resolution.x` * `raw.resolution.y` - 1 | `supervised`
away_race_observed             | ()                                          | int32 | -         | -                                           | always
away_race_requested            | ()                                          | int32 | -         | -                                           | always
camera                         | (`raw.resolution.x`, `raw.resolution.y`)    | int32 | 0         | 1                                           | `raw.camera`
camera_position                | (2,)                                        | int32 | -         | -                                           | `raw.use_camera_position`
camera_size                    | (2,)                                        | int32 | -         | -                                           | `raw.use_camera_position`
game_loop                      | ()                                          | int32 | -         | -                                           | always
home_race_requested            | ()                                          | int32 | -         | -                                           | always
minimap_alerts                 | (`minimap.x`, `minimap.y`)                  | uint8 | 0         | 1                                           | 'alerts' in `minimap features`
minimap_buildable              | (`minimap.x`, `minimap.y`)                  | uint8 | 0         | 1                                           | 'buildable' in `minimap features`
minimap_creep                  | (`minimap.x`, `minimap.y`)                  | uint8 | 0         | 1                                           | 'creep' in `minimap features`
minimap_height_map             | (`minimap.x`, `minimap.y`)                  | uint8 | 0         | 255                                         | 'height_map' in `minimap features`
minimap_pathable               | (`minimap.x`, `minimap.y`)                  | uint8 | 0         | 1                                           | 'pathable' in `minimap features`
minimap_player_relative        | (`minimap.x`, `minimap.y`)                  | uint8 | 0         | 4                                           | 'player_relative' in `minimap features`
minimap_visibility_map         | (`minimap.x`, `minimap.y`)                  | uint8 | 0         | 3                                           | 'visibility_map' in `minimap features`
mmr                            | ()                                          | int32 | -         | -                                           | always
opponent_player                | (10,)                                       | int32 | -         | -                                           | `add_opponent_features`
opponent_unit_counts_bow       | (`num_unit_types`,)                         | int32 | -         | -                                           | `add_opponent_features`
opponent_upgrades_fixed_length | (`max_num_upgrades`,)                       | int32 | 0         | `num_upgrade_types + 1`                     | `add_opponent_features`
player                         | (11,)                                       | int32 | -         | -                                           | always
raw_units                      | (`max_unit_count`, `num_unit_features` + 2) | int32 | 0         | varies                                      | always
unit_counts_bow                | (`num_unit_types`,)                         | int32 | -         | -                                           | always
upgrades_fixed_length          | (`max_num_upgrades`,)                       | int32 | minimum=0 | maximum=`num_upgrade_types` + 1             | always

## Visual mode

If visual settings are provided as part of the converter settings the converter
will operate in visual mode. In this mode the majority of the data provided to
the agent is represented spatially, with planes reflecting the attributes of
units on the screen and minimap. Actions in this mode are more similar to how a
human would interact, point-and-click.

### Action spec

| name              | shape | dtype | min | max                 | enabled? |
| ----------------- | ----- | ----- | --- | ------------------- | -------- |
| function          | ()    | int32 | 0   | `num_action_types`  | always   |
| build_queue_id    | ()    | int32 | 0   | 9                   | always   |
| control_group_act | ()    | int32 | 0   | 4                   | always   |
| control_group_id  | ()    | int32 | 0   | 9                   | always   |
| delay             | ()    | int32 | 1   | 127                 | always   |
| minimap           | ()    | int32 | 0   | `minimap.x` *       | always   |
:                   :       :       :     : `minimap.y` - 1     :          :
| queued            | ()    | int32 | 0   | 1                   | always   |
| screen            | ()    | int32 | 0   | `visual.screen.x` * | always   |
:                   :       :       :     : `visual.screen.y` - :          :
:                   :       :       :     : 1                   :          :
| screen2           | ()    | int32 | 0   | `visual.screen.x` * | always   |
:                   :       :       :     : `visual.screen.y` - :          :
:                   :       :       :     : 1                   :          :
| select_add        | ()    | int32 | 0   | 1                   | always   |
| select_point_act  | ()    | int32 | 0   | 3                   | always   |
| select_unit_act   | ()    | int32 | 0   | 3                   | always   |
| select_unit_id    | ()    | int32 | 0   | 499                 | always   |
| select_worker     | ()    | int32 | 0   | 3                   | always   |
| unload_id         | ()    | int32 | 0   | 499                 | always   |

### Observation spec

name                           | shape                                  | dtype | min | max                                       | enabled?
------------------------------ | -------------------------------------- | ----- | --- | ----------------------------------------- | --------
action/build_queue_id          | ()                                     | int32 | 0   | 9                                         | `supervised`
action/control_group_act       | ()                                     | int32 | 0   | 4                                         | `supervised`
action/control_group_id        | ()                                     | int32 | 0   | 9                                         | `supervised`
action/delay                   | ()                                     | int32 | 1   | 127                                       | `supervised`
action/function                | ()                                     | int32 | 0   | `num_action_types`                        | `supervised`
action/minimap                 | ()                                     | int32 | 0   | `minimap.x` * `minimap.y` - 1             | `supervised`
action/queued                  | ()                                     | int32 | 0   | 1                                         | `supervised`
action/screen                  | ()                                     | int32 | 0   | `visual.screen.x` * `visual.screen.y` - 1 | `supervised`
action/screen2                 | ()                                     | int32 | 0   | `visual.screen.x` * `visual.screen.y` - 1 | `supervised`
action/select_add              | ()                                     | int32 | 0   | 1                                         | `supervised`
action/select_point_act        | ()                                     | int32 | 0   | 3                                         | `supervised`
action/select_unit_act         | ()                                     | int32 | 0   | 3                                         | `supervised`
action/select_unit_id          | ()                                     | int32 | 0   | 499                                       | `supervised`
action/select_worker           | ()                                     | int32 | 0   | 3                                         | `supervised`
action/unload_id               | ()                                     | int32 | 0   | 499                                       | `supervised`
available_actions              | (`num_action_types`,)                  | int32 | -   | -                                         | always
away_race_observed             | ()                                     | int32 | -   | -                                         | always
away_race_requested            | ()                                     | int32 | -   | -                                         | always
game_loop                      | ()                                     | int32 |     | -                                         | -
home_race_requested            | ()                                     | int32 | -   | -                                         | always
minimap_alerts                 | (`minimap.x`, `minimap.y`)             | uint8 | 0   | 1                                         | 'alerts' in `minimap_features`
minimap_buildable              | (`minimap.x`, `minimap.y`)             | uint8 | 0   | 1                                         | 'buildable' in `minimap_features`
minimap_camera                 | (`minimap.x`, `minimap.y`)             | uint8 | 0   | 1                                         | 'camera' in `minimap_features`
minimap_creep                  | (`minimap.x`, `minimap.y`)             | uint8 | 0   | 1                                         | 'creep' in `minimap_features`
minimap_height_map             | (`minimap.x`, `minimap.y`)             | uint8 | 0   | 255                                       | 'height_map' in `minimap_features`
minimap_pathable               | (`minimap.x`, `minimap.y`)             | uint8 | 0   | 1                                         | 'pathable' in `minimap_features`
minimap_player_relative        | (`minimap.x`, `minimap.y`)             | uint8 | 0   | 4                                         | 'player_relative' in `minimap_features`
minimap_selected               | (`minimap.x`, `minimap.y`)             | uint8 | 0   | 1                                         | 'selected' in `minimap_features`
minimap_visibility_map         | (`minimap.x`, `minimap.y`)             | uint8 | 0   | 3                                         | 'visibility_amp' in `minimap_features`
mmr                            | ()                                     | int32 | -   | -                                         | always
opponent_player                | (10,)                                  | int32 | -   | -                                         | `add_opponent_features`
opponent_unit_counts_bow       | (217,)                                 | int32 | -   | -                                         | `add_opponent_features`
opponent_upgrades_fixed_length | (`max_num_upgrades`,)                  | int32 | 0   | `num_upgrade_types` - 1                   | `add_opponent_features`
player                         | (11,)                                  | int32 | -   | -                                         | always
screen_active                  | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 1                                         | 'active' in `visual.screen_features`
screen_blip                    | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 1                                         | 'blip' in `visual.screen_features`
screen_buff_duration           | (`visual.screen.x`, `visual.screen.y`  | uint8 | 0   | 255                                       | 'buff_duration' in `visual.screen_features`
screen_buffs                   | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 47                                        | 'buffs' in `visual.screen_features`
screen_build_progress          | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 255                                       | 'build_progress' in `visual.screen_features`
screen_buildable               | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 1                                         | 'buildable' in `visual.screen_features`
screen_cloaked                 | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 1                                         | 'cloaked' in `visual.screen_features`
screen_creep                   | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 1                                         | 'creep' in `visual.screen_features`
screen_effects                 | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 15                                        | 'effects' in `visual.screen_features`
screen_hallucinations          | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 1                                         | 'hallucinations' in `visual.screen_features`
screen_height_map              | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 255                                       | 'height_map' in `visual.screen_features`
screen_pathable                | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 1                                         | 'pathable' in `visual.screen_features`
screen_player_relative         | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 4                                         | 'player_relative' in `visual.screen_features`
screen_power                   | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 1                                         | 'power' in `visual.screen_features`
screen_selected                | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 1                                         | 'selected' in `visual.screen_features`
screen_unit_density_aa         | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 255                                       | 'unit_density_aa' in `visual.screen_features`
screen_unit_energy_ratio       | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 255                                       | 'unit_energy_ratio' in `visual.screen_features`
screen_unit_hit_points_ratio   | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 255                                       | 'unit_hit_points_ratio' in `visual.screen_features`
screen_unit_shields_ratio      | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 255                                       | 'unit_shields_ratio' in `visual.screen_features`
screen_unit_type               | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | `num_unit_types`                          | 'unit_type' in `visual.screen_features`
screen_visibility_map          | (`visual.screen.x`, `visual.screen.y`) | uint8 | 0   | 3                                         | 'visibility_map' in `visual.screen_features`
unit_counts_bow                | (`num_unit_types`,)                    | int32 | -   | -                                         | always
upgrades_fixed_length          | (`max_num_upgrades`,)                  | int32 | 0   | `num_upgrade_types`-1                     | always
