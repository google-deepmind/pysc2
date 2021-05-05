# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Define the static list of types and actions for SC2."""

import collections
import enum
import numbers

import numpy
from pysc2.lib import point

from s2clientprotocol import spatial_pb2 as sc_spatial
from s2clientprotocol import ui_pb2 as sc_ui


class ActionSpace(enum.Enum):
  FEATURES = 1  # Act in feature layer pixel space with FUNCTIONS below.
  RGB = 2       # Act in RGB pixel space with FUNCTIONS below.
  RAW = 3       # Act with unit tags with RAW_FUNCTIONS below.


def spatial(action, action_space):
  """Choose the action space for the action proto."""
  if action_space == ActionSpace.FEATURES:
    return action.action_feature_layer
  elif action_space == ActionSpace.RGB:
    return action.action_render
  else:
    raise ValueError("Unexpected value for action_space: %s" % action_space)


def no_op(action, action_space):
  del action, action_space


def move_camera(action, action_space, minimap):
  """Move the camera."""
  minimap.assign_to(spatial(action, action_space).camera_move.center_minimap)


def select_point(action, action_space, select_point_act, screen):
  """Select a unit at a point."""
  select = spatial(action, action_space).unit_selection_point
  screen.assign_to(select.selection_screen_coord)
  select.type = select_point_act


def select_rect(action, action_space, select_add, screen, screen2):
  """Select units within a rectangle."""
  select = spatial(action, action_space).unit_selection_rect
  out_rect = select.selection_screen_coord.add()
  screen_rect = point.Rect(screen, screen2)
  screen_rect.tl.assign_to(out_rect.p0)
  screen_rect.br.assign_to(out_rect.p1)
  select.selection_add = bool(select_add)


def select_idle_worker(action, action_space, select_worker):
  """Select an idle worker."""
  del action_space
  action.action_ui.select_idle_worker.type = select_worker


def select_army(action, action_space, select_add):
  """Select the entire army."""
  del action_space
  action.action_ui.select_army.selection_add = select_add


def select_warp_gates(action, action_space, select_add):
  """Select all warp gates."""
  del action_space
  action.action_ui.select_warp_gates.selection_add = select_add


def select_larva(action, action_space):
  """Select all larva."""
  del action_space
  action.action_ui.select_larva.SetInParent()  # Adds the empty proto field.


def select_unit(action, action_space, select_unit_act, select_unit_id):
  """Select a specific unit from the multi-unit selection."""
  del action_space
  select = action.action_ui.multi_panel
  select.type = select_unit_act
  select.unit_index = select_unit_id


def control_group(action, action_space, control_group_act, control_group_id):
  """Act on a control group, selecting, setting, etc."""
  del action_space
  select = action.action_ui.control_group
  select.action = control_group_act
  select.control_group_index = control_group_id


def unload(action, action_space, unload_id):
  """Unload a unit from a transport/bunker/nydus/etc."""
  del action_space
  action.action_ui.cargo_panel.unit_index = unload_id


def build_queue(action, action_space, build_queue_id):
  """Cancel a unit in the build queue."""
  del action_space
  action.action_ui.production_panel.unit_index = build_queue_id


def cmd_quick(action, action_space, ability_id, queued):
  """Do a quick command like 'Stop' or 'Stim'."""
  action_cmd = spatial(action, action_space).unit_command
  action_cmd.ability_id = ability_id
  action_cmd.queue_command = queued


def cmd_screen(action, action_space, ability_id, queued, screen):
  """Do a command that needs a point on the screen."""
  action_cmd = spatial(action, action_space).unit_command
  action_cmd.ability_id = ability_id
  action_cmd.queue_command = queued
  screen.assign_to(action_cmd.target_screen_coord)


def cmd_minimap(action, action_space, ability_id, queued, minimap):
  """Do a command that needs a point on the minimap."""
  action_cmd = spatial(action, action_space).unit_command
  action_cmd.ability_id = ability_id
  action_cmd.queue_command = queued
  minimap.assign_to(action_cmd.target_minimap_coord)


def autocast(action, action_space, ability_id):
  """Toggle autocast."""
  del action_space
  action.action_ui.toggle_autocast.ability_id = ability_id


def raw_no_op(action):
  del action


def raw_move_camera(action, world):
  """Move the camera."""
  action_cmd = action.action_raw.camera_move
  world.assign_to(action_cmd.center_world_space)


def raw_cmd(action, ability_id, queued, unit_tags):
  """Do a raw command to another unit."""
  action_cmd = action.action_raw.unit_command
  action_cmd.ability_id = ability_id
  action_cmd.queue_command = queued
  if not isinstance(unit_tags, (tuple, list)):
    unit_tags = [unit_tags]
  action_cmd.unit_tags.extend(unit_tags)


def raw_cmd_pt(action, ability_id, queued, unit_tags, world):
  """Do a raw command to another unit towards a point."""
  action_cmd = action.action_raw.unit_command
  action_cmd.ability_id = ability_id
  action_cmd.queue_command = queued
  if not isinstance(unit_tags, (tuple, list)):
    unit_tags = [unit_tags]
  action_cmd.unit_tags.extend(unit_tags)
  world.assign_to(action_cmd.target_world_space_pos)


def raw_cmd_unit(action, ability_id, queued, unit_tags,
                 target_unit_tag):
  """Do a raw command to another unit towards a unit."""
  action_cmd = action.action_raw.unit_command
  action_cmd.ability_id = ability_id
  action_cmd.queue_command = queued
  if not isinstance(unit_tags, (tuple, list)):
    unit_tags = [unit_tags]
  action_cmd.unit_tags.extend(unit_tags)
  action_cmd.target_unit_tag = target_unit_tag


def raw_autocast(action, ability_id, unit_tags):
  """Toggle autocast."""
  action_cmd = action.action_raw.toggle_autocast
  action_cmd.ability_id = ability_id
  if not isinstance(unit_tags, (tuple, list)):
    unit_tags = [unit_tags]
  action_cmd.unit_tags.extend(unit_tags)


def numpy_to_python(val):
  """Convert numpy types to their corresponding python types."""
  if isinstance(val, (int, float)):
    return val
  if isinstance(val, str):
    return val
  if (isinstance(val, numpy.number) or
      isinstance(val, numpy.ndarray) and not val.shape):  # numpy.array(1)
    return val.item()
  if isinstance(val, (list, tuple, numpy.ndarray)):
    return [numpy_to_python(v) for v in val]
  raise ValueError("Unknown value. Type: %s, repr: %s" % (type(val), repr(val)))


class ArgumentType(collections.namedtuple(
    "ArgumentType", ["id", "name", "sizes", "fn", "values", "count"])):
  """Represents a single argument type.

  Attributes:
    id: The argument id. This is unique.
    name: The name of the argument, also unique.
    sizes: The max+1 of each of the dimensions this argument takes.
    fn: The function to convert the list of integers into something more
        meaningful to be set in the protos to send to the game.
    values: An enum representing the values this argument type could hold. None
        if this isn't an enum argument type.
    count: Number of valid values. Only useful for unit_tags.
  """
  __slots__ = ()

  def __str__(self):
    return "%s/%s %s" % (self.id, self.name, list(self.sizes))

  def __reduce__(self):
    return self.__class__, tuple(self)

  @classmethod
  def enum(cls, options, values):
    """Create an ArgumentType where you choose one of a set of known values."""
    names, real = zip(*options)
    del names  # unused

    def factory(i, name):
      return cls(i, name, (len(real),), lambda a: real[a[0]], values, None)
    return factory

  @classmethod
  def scalar(cls, value):
    """Create an ArgumentType with a single scalar in range(value)."""
    return lambda i, name: cls(i, name, (value,), lambda a: a[0], None, None)

  @classmethod
  def point(cls):  # No range because it's unknown at this time.
    """Create an ArgumentType that is represented by a point.Point."""
    def factory(i, name):
      return cls(i, name, (0, 0), lambda a: point.Point(*a).floor(), None, None)
    return factory

  @classmethod
  def spec(cls, id_, name, sizes):
    """Create an ArgumentType to be used in ValidActions."""
    return cls(id_, name, sizes, None, None, None)

  @classmethod
  def unit_tags(cls, count, size):
    """Create an ArgumentType with a list of unbounded ints."""
    def clean(arg):
      arg = numpy_to_python(arg)
      if isinstance(arg, list) and len(arg) == 1 and isinstance(arg[0], list):
        arg = arg[0]  # Support [[list, of, tags]].
      return arg[:count]
    return lambda i, name: cls(i, name, (size,), clean, None, count)


class Arguments(collections.namedtuple("Arguments", [
    "screen", "minimap", "screen2", "queued", "control_group_act",
    "control_group_id", "select_point_act", "select_add", "select_unit_act",
    "select_unit_id", "select_worker", "build_queue_id", "unload_id"])):
  """The full list of argument types.

  Take a look at TYPES and FUNCTION_TYPES for more details.

  Attributes:
    screen: A point on the screen.
    minimap: A point on the minimap.
    screen2: The second point for a rectangle. This is needed so that no
        function takes the same type twice.
    queued: Whether the action should be done immediately or after all other
        actions queued for this unit.
    control_group_act: What to do with the control group.
    control_group_id: Which control group to do it with.
    select_point_act: What to do with the unit at the point.
    select_add: Whether to add the unit to the selection or replace it.
    select_unit_act: What to do when selecting a unit by id.
    select_unit_id: Which unit to select by id.
    select_worker: What to do when selecting a worker.
    build_queue_id: Which build queue index to target.
    unload_id: Which unit to target in a transport/nydus/command center.
  """
  __slots__ = ()

  @classmethod
  def types(cls, **kwargs):
    """Create an Arguments of the possible Types."""
    named = {name: factory(Arguments._fields.index(name), name)
             for name, factory in kwargs.items()}
    return cls(**named)

  def __reduce__(self):
    return self.__class__, tuple(self)


class RawArguments(collections.namedtuple("RawArguments", [
    "world", "queued", "unit_tags", "target_unit_tag"])):
  """The full list of argument types.

  Take a look at TYPES and FUNCTION_TYPES for more details.

  Attributes:
    world: A point in world coordinates
    queued: Whether the action should be done immediately or after all other
        actions queued for this unit.
    unit_tags: Which units should execute this action.
    target_unit_tag: The target unit of this action.
  """
  __slots__ = ()

  @classmethod
  def types(cls, **kwargs):
    """Create an Arguments of the possible Types."""
    named = {name: factory(RawArguments._fields.index(name), name)
             for name, factory in kwargs.items()}
    return cls(**named)

  def __reduce__(self):
    return self.__class__, tuple(self)


def _define_position_based_enum(name, options):
  return enum.IntEnum(
      name, {opt_name: i for i, (opt_name, _) in enumerate(options)})


QUEUED_OPTIONS = [
    ("now", False),
    ("queued", True),
]
Queued = _define_position_based_enum(  # pylint: disable=invalid-name
    "Queued", QUEUED_OPTIONS)

CONTROL_GROUP_ACT_OPTIONS = [
    ("recall", sc_ui.ActionControlGroup.Recall),
    ("set", sc_ui.ActionControlGroup.Set),
    ("append", sc_ui.ActionControlGroup.Append),
    ("set_and_steal", sc_ui.ActionControlGroup.SetAndSteal),
    ("append_and_steal", sc_ui.ActionControlGroup.AppendAndSteal),
]
ControlGroupAct = _define_position_based_enum(  # pylint: disable=invalid-name
    "ControlGroupAct", CONTROL_GROUP_ACT_OPTIONS)

SELECT_POINT_ACT_OPTIONS = [
    ("select", sc_spatial.ActionSpatialUnitSelectionPoint.Select),
    ("toggle", sc_spatial.ActionSpatialUnitSelectionPoint.Toggle),
    ("select_all_type", sc_spatial.ActionSpatialUnitSelectionPoint.AllType),
    ("add_all_type", sc_spatial.ActionSpatialUnitSelectionPoint.AddAllType),
]
SelectPointAct = _define_position_based_enum(  # pylint: disable=invalid-name
    "SelectPointAct", SELECT_POINT_ACT_OPTIONS)

SELECT_ADD_OPTIONS = [
    ("select", False),
    ("add", True),
]
SelectAdd = _define_position_based_enum(  # pylint: disable=invalid-name
    "SelectAdd", SELECT_ADD_OPTIONS)

SELECT_UNIT_ACT_OPTIONS = [
    ("select", sc_ui.ActionMultiPanel.SingleSelect),
    ("deselect", sc_ui.ActionMultiPanel.DeselectUnit),
    ("select_all_type", sc_ui.ActionMultiPanel.SelectAllOfType),
    ("deselect_all_type", sc_ui.ActionMultiPanel.DeselectAllOfType),
]
SelectUnitAct = _define_position_based_enum(  # pylint: disable=invalid-name
    "SelectUnitAct", SELECT_UNIT_ACT_OPTIONS)

SELECT_WORKER_OPTIONS = [
    ("select", sc_ui.ActionSelectIdleWorker.Set),
    ("add", sc_ui.ActionSelectIdleWorker.Add),
    ("select_all", sc_ui.ActionSelectIdleWorker.All),
    ("add_all", sc_ui.ActionSelectIdleWorker.AddAll),
]
SelectWorker = _define_position_based_enum(  # pylint: disable=invalid-name
    "SelectWorker", SELECT_WORKER_OPTIONS)


# The list of known types.
TYPES = Arguments.types(
    screen=ArgumentType.point(),
    minimap=ArgumentType.point(),
    screen2=ArgumentType.point(),
    queued=ArgumentType.enum(QUEUED_OPTIONS, Queued),
    control_group_act=ArgumentType.enum(
        CONTROL_GROUP_ACT_OPTIONS, ControlGroupAct),
    control_group_id=ArgumentType.scalar(10),
    select_point_act=ArgumentType.enum(
        SELECT_POINT_ACT_OPTIONS, SelectPointAct),
    select_add=ArgumentType.enum(SELECT_ADD_OPTIONS, SelectAdd),
    select_unit_act=ArgumentType.enum(SELECT_UNIT_ACT_OPTIONS, SelectUnitAct),
    select_unit_id=ArgumentType.scalar(500),  # Depends on current selection.
    select_worker=ArgumentType.enum(SELECT_WORKER_OPTIONS, SelectWorker),
    build_queue_id=ArgumentType.scalar(10),  # Depends on current build queue.
    unload_id=ArgumentType.scalar(500),  # Depends on the current loaded units.
)

RAW_TYPES = RawArguments.types(
    world=ArgumentType.point(),
    queued=ArgumentType.enum(QUEUED_OPTIONS, Queued),
    unit_tags=ArgumentType.unit_tags(512, 512),
    target_unit_tag=ArgumentType.unit_tags(1, 512),
)


# Which argument types do each function need?
FUNCTION_TYPES = {
    no_op: [],
    move_camera: [TYPES.minimap],
    select_point: [TYPES.select_point_act, TYPES.screen],
    select_rect: [TYPES.select_add, TYPES.screen, TYPES.screen2],
    select_unit: [TYPES.select_unit_act, TYPES.select_unit_id],
    control_group: [TYPES.control_group_act, TYPES.control_group_id],
    select_idle_worker: [TYPES.select_worker],
    select_army: [TYPES.select_add],
    select_warp_gates: [TYPES.select_add],
    select_larva: [],
    unload: [TYPES.unload_id],
    build_queue: [TYPES.build_queue_id],
    cmd_quick: [TYPES.queued],
    cmd_screen: [TYPES.queued, TYPES.screen],
    cmd_minimap: [TYPES.queued, TYPES.minimap],
    autocast: [],
    raw_no_op: [],
    raw_cmd: [RAW_TYPES.queued, RAW_TYPES.unit_tags],
    raw_cmd_pt: [RAW_TYPES.queued, RAW_TYPES.unit_tags, RAW_TYPES.world],
    raw_cmd_unit: [RAW_TYPES.queued, RAW_TYPES.unit_tags,
                   RAW_TYPES.target_unit_tag],
    raw_move_camera: [RAW_TYPES.world],
    raw_autocast: [RAW_TYPES.unit_tags],
}

# Which ones need an ability?
ABILITY_FUNCTIONS = {cmd_quick, cmd_screen, cmd_minimap, autocast}
RAW_ABILITY_FUNCTIONS = {raw_cmd, raw_cmd_pt, raw_cmd_unit, raw_autocast}

# Which ones require a point?
POINT_REQUIRED_FUNCS = {
    False: {cmd_quick, autocast},
    True: {cmd_screen, cmd_minimap, autocast}}

always = lambda _: True


class Function(collections.namedtuple(
    "Function", ["id", "name", "ability_id", "general_id", "function_type",
                 "args", "avail_fn", "raw"])):
  """Represents a function action.

  Attributes:
    id: The function id, which is what the agent will use.
    name: The name of the function. Should be unique.
    ability_id: The ability id to pass to sc2.
    general_id: 0 for normal abilities, and the ability_id of another ability if
        it can be represented by a more general action.
    function_type: One of the functions in FUNCTION_TYPES for how to construct
        the sc2 action proto out of python types.
    args: A list of the types of args passed to function_type.
    avail_fn: For non-abilities, this function returns whether the function is
        valid.
    raw: Whether the function is raw or not.
  """
  __slots__ = ()

  @classmethod
  def ui_func(cls, id_, name, function_type, avail_fn=always):
    """Define a function representing a ui action."""
    return cls(id_, name, 0, 0, function_type, FUNCTION_TYPES[function_type],
               avail_fn, False)

  @classmethod
  def ability(cls, id_, name, function_type, ability_id, general_id=0):
    """Define a function represented as a game ability."""
    assert function_type in ABILITY_FUNCTIONS
    return cls(id_, name, ability_id, general_id, function_type,
               FUNCTION_TYPES[function_type], None, False)

  @classmethod
  def raw_ability(cls, id_, name, function_type, ability_id, general_id=0,
                  avail_fn=always):
    """Define a function represented as a game ability."""
    assert function_type in RAW_ABILITY_FUNCTIONS
    return cls(id_, name, ability_id, general_id, function_type,
               FUNCTION_TYPES[function_type], avail_fn, True)

  @classmethod
  def raw_ui_func(cls, id_, name, function_type, avail_fn=always):
    """Define a function representing a ui action."""
    return cls(id_, name, 0, 0, function_type, FUNCTION_TYPES[function_type],
               avail_fn, True)

  @classmethod
  def spec(cls, id_, name, args):
    """Create a Function to be used in ValidActions."""
    return cls(id_, name, None, None, None, args, None, False)

  def __hash__(self):  # So it can go in a set().
    return self.id

  def __str__(self):
    return self.str()

  def __call__(self, *args):
    """A convenient way to create a FunctionCall from this Function."""
    return FunctionCall.init_with_validation(self.id, args, raw=self.raw)

  def __reduce__(self):
    return self.__class__, tuple(self)

  def str(self, space=False):
    """String version. Set space=True to line them all up nicely."""
    return "%s/%s (%s)" % (str(int(self.id)).rjust(space and 4),
                           self.name.ljust(space and 50),
                           "; ".join(str(a) for a in self.args))


class Functions(object):
  """Represents the full set of functions.

  Can't use namedtuple since python3 has a limit of 255 function arguments, so
  build something similar.
  """

  def __init__(self, functions):
    functions = sorted(functions, key=lambda f: f.id)
    self._func_list = functions
    self._func_dict = {f.name: f for f in functions}
    if len(self._func_dict) != len(self._func_list):
      raise ValueError("Function names must be unique.")

  def __getattr__(self, name):
    return self._func_dict[name]

  def __getitem__(self, key):
    if isinstance(key, numbers.Integral):
      return self._func_list[key]
    return self._func_dict[key]

  def __getstate__(self):
    # Support pickling, which otherwise conflicts with __getattr__.
    return self._func_list

  def __setstate__(self, functions):
    # Support pickling, which otherwise conflicts with __getattr__.
    self.__init__(functions)

  def __iter__(self):
    return iter(self._func_list)

  def __len__(self):
    return len(self._func_list)

  def __eq__(self, other):
    return self._func_list == other._func_list  # pylint: disable=protected-access


# The semantic meaning of these actions can mainly be found by searching:
# http://liquipedia.net/starcraft2/ or http://starcraft.wikia.com/ .
# pylint: disable=line-too-long
_FUNCTIONS = [
    Function.ui_func(0, "no_op", no_op),
    Function.ui_func(1, "move_camera", move_camera),
    Function.ui_func(2, "select_point", select_point),
    Function.ui_func(3, "select_rect", select_rect),
    Function.ui_func(4, "select_control_group", control_group),
    Function.ui_func(5, "select_unit", select_unit,
                     lambda obs: obs.ui_data.HasField("multi")),
    Function.ui_func(6, "select_idle_worker", select_idle_worker,
                     lambda obs: obs.player_common.idle_worker_count > 0),
    Function.ui_func(7, "select_army", select_army,
                     lambda obs: obs.player_common.army_count > 0),
    Function.ui_func(8, "select_warp_gates", select_warp_gates,
                     lambda obs: obs.player_common.warp_gate_count > 0),
    Function.ui_func(9, "select_larva", select_larva,
                     lambda obs: obs.player_common.larva_count > 0),
    Function.ui_func(10, "unload", unload,
                     lambda obs: obs.ui_data.HasField("cargo")),
    Function.ui_func(11, "build_queue", build_queue,
                     lambda obs: obs.ui_data.HasField("production")),
    # Everything below here is generated with gen_actions.py
    Function.ability(12, "Attack_screen", cmd_screen, 3674),
    Function.ability(13, "Attack_minimap", cmd_minimap, 3674),
    Function.ability(14, "Attack_Attack_screen", cmd_screen, 23, 3674),
    Function.ability(15, "Attack_Attack_minimap", cmd_minimap, 23, 3674),
    Function.ability(16, "Attack_AttackBuilding_screen", cmd_screen, 2048, 3674),
    Function.ability(17, "Attack_AttackBuilding_minimap", cmd_minimap, 2048, 3674),
    Function.ability(555, "Attack_Battlecruiser_screen", cmd_screen, 3771, 3674),
    Function.ability(556, "Attack_Battlecruiser_minimap", cmd_minimap, 3771, 3674),
    Function.ability(18, "Attack_Redirect_screen", cmd_screen, 1682, 3674),
    Function.ability(19, "Scan_Move_screen", cmd_screen, 19, 3674),
    Function.ability(20, "Scan_Move_minimap", cmd_minimap, 19, 3674),
    Function.ability(21, "Behavior_BuildingAttackOff_quick", cmd_quick, 2082),
    Function.ability(22, "Behavior_BuildingAttackOn_quick", cmd_quick, 2081),
    Function.ability(23, "Behavior_CloakOff_quick", cmd_quick, 3677),
    Function.ability(24, "Behavior_CloakOff_Banshee_quick", cmd_quick, 393, 3677),
    Function.ability(25, "Behavior_CloakOff_Ghost_quick", cmd_quick, 383, 3677),
    Function.ability(26, "Behavior_CloakOn_quick", cmd_quick, 3676),
    Function.ability(27, "Behavior_CloakOn_Banshee_quick", cmd_quick, 392, 3676),
    Function.ability(28, "Behavior_CloakOn_Ghost_quick", cmd_quick, 382, 3676),
    Function.ability(29, "Behavior_GenerateCreepOff_quick", cmd_quick, 1693),
    Function.ability(30, "Behavior_GenerateCreepOn_quick", cmd_quick, 1692),
    Function.ability(31, "Behavior_HoldFireOff_quick", cmd_quick, 3689),
    Function.ability(32, "Behavior_HoldFireOff_Ghost_quick", cmd_quick, 38, 3689),
    Function.ability(33, "Behavior_HoldFireOff_Lurker_quick", cmd_quick, 2552, 3689),
    Function.ability(34, "Behavior_HoldFireOn_quick", cmd_quick, 3688),
    Function.ability(35, "Behavior_HoldFireOn_Ghost_quick", cmd_quick, 36, 3688),
    Function.ability(36, "Behavior_HoldFireOn_Lurker_quick", cmd_quick, 2550, 3688),
    Function.ability(37, "Behavior_PulsarBeamOff_quick", cmd_quick, 2376),
    Function.ability(38, "Behavior_PulsarBeamOn_quick", cmd_quick, 2375),
    Function.ability(39, "Build_Armory_screen", cmd_screen, 331),
    Function.ability(40, "Build_Assimilator_screen", cmd_screen, 882),
    Function.ability(41, "Build_BanelingNest_screen", cmd_screen, 1162),
    Function.ability(42, "Build_Barracks_screen", cmd_screen, 321),
    Function.ability(43, "Build_Bunker_screen", cmd_screen, 324),
    Function.ability(44, "Build_CommandCenter_screen", cmd_screen, 318),
    Function.ability(45, "Build_CreepTumor_screen", cmd_screen, 3691),
    Function.ability(46, "Build_CreepTumor_Queen_screen", cmd_screen, 1694, 3691),
    Function.ability(47, "Build_CreepTumor_Tumor_screen", cmd_screen, 1733, 3691),
    Function.ability(48, "Build_CyberneticsCore_screen", cmd_screen, 894),
    Function.ability(49, "Build_DarkShrine_screen", cmd_screen, 891),
    Function.ability(50, "Build_EngineeringBay_screen", cmd_screen, 322),
    Function.ability(51, "Build_EvolutionChamber_screen", cmd_screen, 1156),
    Function.ability(52, "Build_Extractor_screen", cmd_screen, 1154),
    Function.ability(53, "Build_Factory_screen", cmd_screen, 328),
    Function.ability(54, "Build_FleetBeacon_screen", cmd_screen, 885),
    Function.ability(55, "Build_Forge_screen", cmd_screen, 884),
    Function.ability(56, "Build_FusionCore_screen", cmd_screen, 333),
    Function.ability(57, "Build_Gateway_screen", cmd_screen, 883),
    Function.ability(58, "Build_GhostAcademy_screen", cmd_screen, 327),
    Function.ability(59, "Build_Hatchery_screen", cmd_screen, 1152),
    Function.ability(60, "Build_HydraliskDen_screen", cmd_screen, 1157),
    Function.ability(61, "Build_InfestationPit_screen", cmd_screen, 1160),
    Function.ability(62, "Build_Interceptors_quick", cmd_quick, 1042),
    Function.ability(63, "Build_Interceptors_autocast", autocast, 1042),
    Function.ability(524, "Build_LurkerDen_screen", cmd_screen, 1163),
    Function.ability(64, "Build_MissileTurret_screen", cmd_screen, 323),
    Function.ability(65, "Build_Nexus_screen", cmd_screen, 880),
    Function.ability(66, "Build_Nuke_quick", cmd_quick, 710),
    Function.ability(67, "Build_NydusNetwork_screen", cmd_screen, 1161),
    Function.ability(68, "Build_NydusWorm_screen", cmd_screen, 1768),
    Function.ability(69, "Build_PhotonCannon_screen", cmd_screen, 887),
    Function.ability(70, "Build_Pylon_screen", cmd_screen, 881),
    Function.ability(71, "Build_Reactor_quick", cmd_quick, 3683),
    Function.ability(72, "Build_Reactor_screen", cmd_screen, 3683),
    Function.ability(73, "Build_Reactor_Barracks_quick", cmd_quick, 422, 3683),
    Function.ability(74, "Build_Reactor_Barracks_screen", cmd_screen, 422, 3683),
    Function.ability(75, "Build_Reactor_Factory_quick", cmd_quick, 455, 3683),
    Function.ability(76, "Build_Reactor_Factory_screen", cmd_screen, 455, 3683),
    Function.ability(77, "Build_Reactor_Starport_quick", cmd_quick, 488, 3683),
    Function.ability(78, "Build_Reactor_Starport_screen", cmd_screen, 488, 3683),
    Function.ability(79, "Build_Refinery_screen", cmd_screen, 320),
    Function.ability(80, "Build_RoachWarren_screen", cmd_screen, 1165),
    Function.ability(81, "Build_RoboticsBay_screen", cmd_screen, 892),
    Function.ability(82, "Build_RoboticsFacility_screen", cmd_screen, 893),
    Function.ability(83, "Build_SensorTower_screen", cmd_screen, 326),
    Function.ability(525, "Build_ShieldBattery_screen", cmd_screen, 895),
    Function.ability(84, "Build_SpawningPool_screen", cmd_screen, 1155),
    Function.ability(85, "Build_SpineCrawler_screen", cmd_screen, 1166),
    Function.ability(86, "Build_Spire_screen", cmd_screen, 1158),
    Function.ability(87, "Build_SporeCrawler_screen", cmd_screen, 1167),
    Function.ability(88, "Build_Stargate_screen", cmd_screen, 889),
    Function.ability(89, "Build_Starport_screen", cmd_screen, 329),
    Function.ability(90, "Build_StasisTrap_screen", cmd_screen, 2505),
    Function.ability(91, "Build_SupplyDepot_screen", cmd_screen, 319),
    Function.ability(92, "Build_TechLab_quick", cmd_quick, 3682),
    Function.ability(93, "Build_TechLab_screen", cmd_screen, 3682),
    Function.ability(94, "Build_TechLab_Barracks_quick", cmd_quick, 421, 3682),
    Function.ability(95, "Build_TechLab_Barracks_screen", cmd_screen, 421, 3682),
    Function.ability(96, "Build_TechLab_Factory_quick", cmd_quick, 454, 3682),
    Function.ability(97, "Build_TechLab_Factory_screen", cmd_screen, 454, 3682),
    Function.ability(98, "Build_TechLab_Starport_quick", cmd_quick, 487, 3682),
    Function.ability(99, "Build_TechLab_Starport_screen", cmd_screen, 487, 3682),
    Function.ability(100, "Build_TemplarArchive_screen", cmd_screen, 890),
    Function.ability(101, "Build_TwilightCouncil_screen", cmd_screen, 886),
    Function.ability(102, "Build_UltraliskCavern_screen", cmd_screen, 1159),
    Function.ability(103, "BurrowDown_quick", cmd_quick, 3661),
    Function.ability(104, "BurrowDown_Baneling_quick", cmd_quick, 1374, 3661),
    Function.ability(105, "BurrowDown_Drone_quick", cmd_quick, 1378, 3661),
    Function.ability(106, "BurrowDown_Hydralisk_quick", cmd_quick, 1382, 3661),
    Function.ability(107, "BurrowDown_Infestor_quick", cmd_quick, 1444, 3661),
    Function.ability(108, "BurrowDown_InfestorTerran_quick", cmd_quick, 1394, 3661),
    Function.ability(109, "BurrowDown_Lurker_quick", cmd_quick, 2108, 3661),
    Function.ability(110, "BurrowDown_Queen_quick", cmd_quick, 1433, 3661),
    Function.ability(111, "BurrowDown_Ravager_quick", cmd_quick, 2340, 3661),
    Function.ability(112, "BurrowDown_Roach_quick", cmd_quick, 1386, 3661),
    Function.ability(113, "BurrowDown_SwarmHost_quick", cmd_quick, 2014, 3661),
    Function.ability(114, "BurrowDown_Ultralisk_quick", cmd_quick, 1512, 3661),
    Function.ability(115, "BurrowDown_WidowMine_quick", cmd_quick, 2095, 3661),
    Function.ability(116, "BurrowDown_Zergling_quick", cmd_quick, 1390, 3661),
    Function.ability(117, "BurrowUp_quick", cmd_quick, 3662),
    Function.ability(118, "BurrowUp_autocast", autocast, 3662),
    Function.ability(119, "BurrowUp_Baneling_quick", cmd_quick, 1376, 3662),
    Function.ability(120, "BurrowUp_Baneling_autocast", autocast, 1376, 3662),
    Function.ability(121, "BurrowUp_Drone_quick", cmd_quick, 1380, 3662),
    Function.ability(122, "BurrowUp_Hydralisk_quick", cmd_quick, 1384, 3662),
    Function.ability(123, "BurrowUp_Hydralisk_autocast", autocast, 1384, 3662),
    Function.ability(124, "BurrowUp_Infestor_quick", cmd_quick, 1446, 3662),
    Function.ability(125, "BurrowUp_InfestorTerran_quick", cmd_quick, 1396, 3662),
    Function.ability(126, "BurrowUp_InfestorTerran_autocast", autocast, 1396, 3662),
    Function.ability(127, "BurrowUp_Lurker_quick", cmd_quick, 2110, 3662),
    Function.ability(128, "BurrowUp_Queen_quick", cmd_quick, 1435, 3662),
    Function.ability(129, "BurrowUp_Queen_autocast", autocast, 1435, 3662),
    Function.ability(130, "BurrowUp_Ravager_quick", cmd_quick, 2342, 3662),
    Function.ability(131, "BurrowUp_Ravager_autocast", autocast, 2342, 3662),
    Function.ability(132, "BurrowUp_Roach_quick", cmd_quick, 1388, 3662),
    Function.ability(133, "BurrowUp_Roach_autocast", autocast, 1388, 3662),
    Function.ability(134, "BurrowUp_SwarmHost_quick", cmd_quick, 2016, 3662),
    Function.ability(135, "BurrowUp_Ultralisk_quick", cmd_quick, 1514, 3662),
    Function.ability(136, "BurrowUp_Ultralisk_autocast", autocast, 1514, 3662),
    Function.ability(137, "BurrowUp_WidowMine_quick", cmd_quick, 2097, 3662),
    Function.ability(138, "BurrowUp_Zergling_quick", cmd_quick, 1392, 3662),
    Function.ability(139, "BurrowUp_Zergling_autocast", autocast, 1392, 3662),
    Function.ability(140, "Cancel_quick", cmd_quick, 3659),
    Function.ability(141, "Cancel_AdeptPhaseShift_quick", cmd_quick, 2594, 3659),
    Function.ability(142, "Cancel_AdeptShadePhaseShift_quick", cmd_quick, 2596, 3659),
    Function.ability(143, "Cancel_BarracksAddOn_quick", cmd_quick, 451, 3659),
    Function.ability(144, "Cancel_BuildInProgress_quick", cmd_quick, 314, 3659),
    Function.ability(145, "Cancel_CreepTumor_quick", cmd_quick, 1763, 3659),
    Function.ability(146, "Cancel_FactoryAddOn_quick", cmd_quick, 484, 3659),
    Function.ability(147, "Cancel_GravitonBeam_quick", cmd_quick, 174, 3659),
    Function.ability(148, "Cancel_LockOn_quick", cmd_quick, 2354, 3659),
    Function.ability(149, "Cancel_MorphBroodlord_quick", cmd_quick, 1373, 3659),
    Function.ability(150, "Cancel_MorphGreaterSpire_quick", cmd_quick, 1221, 3659),
    Function.ability(151, "Cancel_MorphHive_quick", cmd_quick, 1219, 3659),
    Function.ability(152, "Cancel_MorphLair_quick", cmd_quick, 1217, 3659),
    Function.ability(153, "Cancel_MorphLurker_quick", cmd_quick, 2333, 3659),
    Function.ability(154, "Cancel_MorphLurkerDen_quick", cmd_quick, 2113, 3659),
    Function.ability(155, "Cancel_MorphMothership_quick", cmd_quick, 1848, 3659),
    Function.ability(156, "Cancel_MorphOrbital_quick", cmd_quick, 1517, 3659),
    Function.ability(157, "Cancel_MorphOverlordTransport_quick", cmd_quick, 2709, 3659),
    Function.ability(158, "Cancel_MorphOverseer_quick", cmd_quick, 1449, 3659),
    Function.ability(159, "Cancel_MorphPlanetaryFortress_quick", cmd_quick, 1451, 3659),
    Function.ability(160, "Cancel_MorphRavager_quick", cmd_quick, 2331, 3659),
    Function.ability(161, "Cancel_MorphThorExplosiveMode_quick", cmd_quick, 2365, 3659),
    Function.ability(162, "Cancel_NeuralParasite_quick", cmd_quick, 250, 3659),
    Function.ability(163, "Cancel_Nuke_quick", cmd_quick, 1623, 3659),
    Function.ability(164, "Cancel_SpineCrawlerRoot_quick", cmd_quick, 1730, 3659),
    Function.ability(165, "Cancel_SporeCrawlerRoot_quick", cmd_quick, 1732, 3659),
    Function.ability(166, "Cancel_StarportAddOn_quick", cmd_quick, 517, 3659),
    Function.ability(167, "Cancel_StasisTrap_quick", cmd_quick, 2535, 3659),
    Function.ability(546, "Cancel_VoidRayPrismaticAlignment_quick", cmd_quick, 3707, 3659),
    Function.ability(168, "Cancel_Last_quick", cmd_quick, 3671),
    Function.ability(169, "Cancel_HangarQueue5_quick", cmd_quick, 1038, 3671),
    Function.ability(170, "Cancel_Queue1_quick", cmd_quick, 304, 3671),
    Function.ability(171, "Cancel_Queue5_quick", cmd_quick, 306, 3671),
    Function.ability(172, "Cancel_QueueAddOn_quick", cmd_quick, 312, 3671),
    Function.ability(173, "Cancel_QueueCancelToSelection_quick", cmd_quick, 308, 3671),
    Function.ability(174, "Cancel_QueuePassive_quick", cmd_quick, 1831, 3671),
    Function.ability(175, "Cancel_QueuePassiveCancelToSelection_quick", cmd_quick, 1833, 3671),
    Function.ability(176, "Effect_Abduct_screen", cmd_screen, 2067),
    Function.ability(177, "Effect_AdeptPhaseShift_screen", cmd_screen, 2544),
    Function.ability(547, "Effect_AdeptPhaseShift_minimap", cmd_minimap, 2544),
    Function.ability(526, "Effect_AntiArmorMissile_screen", cmd_screen, 3753),
    Function.ability(178, "Effect_AutoTurret_screen", cmd_screen, 1764),
    Function.ability(179, "Effect_BlindingCloud_screen", cmd_screen, 2063),
    Function.ability(180, "Effect_Blink_screen", cmd_screen, 3687),
    Function.ability(543, "Effect_Blink_minimap", cmd_minimap, 3687),
    Function.ability(181, "Effect_Blink_Stalker_screen", cmd_screen, 1442, 3687),
    Function.ability(544, "Effect_Blink_Stalker_minimap", cmd_minimap, 1442, 3687),
    Function.ability(182, "Effect_ShadowStride_screen", cmd_screen, 2700, 3687),
    Function.ability(545, "Effect_ShadowStride_minimap", cmd_minimap, 2700, 3687),
    Function.ability(183, "Effect_CalldownMULE_screen", cmd_screen, 171),
    Function.ability(184, "Effect_CausticSpray_screen", cmd_screen, 2324),
    Function.ability(185, "Effect_Charge_screen", cmd_screen, 1819),
    Function.ability(186, "Effect_Charge_autocast", autocast, 1819),
    Function.ability(187, "Effect_ChronoBoost_screen", cmd_screen, 261),
    Function.ability(527, "Effect_ChronoBoostEnergyCost_screen", cmd_screen, 3755),
    Function.ability(188, "Effect_Contaminate_screen", cmd_screen, 1825),
    Function.ability(189, "Effect_CorrosiveBile_screen", cmd_screen, 2338),
    Function.ability(190, "Effect_EMP_screen", cmd_screen, 1628),
    Function.ability(191, "Effect_Explode_quick", cmd_quick, 42),
    Function.ability(192, "Effect_Feedback_screen", cmd_screen, 140),
    Function.ability(193, "Effect_ForceField_screen", cmd_screen, 1526),
    Function.ability(194, "Effect_FungalGrowth_screen", cmd_screen, 74),
    Function.ability(195, "Effect_GhostSnipe_screen", cmd_screen, 2714),
    Function.ability(196, "Effect_GravitonBeam_screen", cmd_screen, 173),
    Function.ability(197, "Effect_GuardianShield_quick", cmd_quick, 76),
    Function.ability(198, "Effect_Heal_screen", cmd_screen, 386),
    Function.ability(199, "Effect_Heal_autocast", autocast, 386),
    Function.ability(200, "Effect_HunterSeekerMissile_screen", cmd_screen, 169),
    Function.ability(201, "Effect_ImmortalBarrier_quick", cmd_quick, 2328),
    Function.ability(202, "Effect_ImmortalBarrier_autocast", autocast, 2328),
    Function.ability(203, "Effect_InfestedTerrans_screen", cmd_screen, 247),
    Function.ability(204, "Effect_InjectLarva_screen", cmd_screen, 251),
    Function.ability(528, "Effect_InterferenceMatrix_screen", cmd_screen, 3747),
    Function.ability(205, "Effect_KD8Charge_screen", cmd_screen, 2588),
    Function.ability(206, "Effect_LockOn_screen", cmd_screen, 2350),
    Function.ability(557, "Effect_LockOn_autocast", autocast, 2350),
    Function.ability(207, "Effect_LocustSwoop_screen", cmd_screen, 2387),
    Function.ability(208, "Effect_MassRecall_screen", cmd_screen, 3686),
    Function.ability(209, "Effect_MassRecall_Mothership_screen", cmd_screen, 2368, 3686),
    Function.ability(210, "Effect_MassRecall_MothershipCore_screen", cmd_screen, 1974, 3686),
    Function.ability(529, "Effect_MassRecall_Nexus_screen", cmd_screen, 3757, 3686),
    Function.ability(548, "Effect_MassRecall_StrategicRecall_screen", cmd_screen, 142, 3686),
    Function.ability(211, "Effect_MedivacIgniteAfterburners_quick", cmd_quick, 2116),
    Function.ability(212, "Effect_NeuralParasite_screen", cmd_screen, 249),
    Function.ability(213, "Effect_NukeCalldown_screen", cmd_screen, 1622),
    Function.ability(214, "Effect_OracleRevelation_screen", cmd_screen, 2146),
    Function.ability(215, "Effect_ParasiticBomb_screen", cmd_screen, 2542),
    Function.ability(216, "Effect_PhotonOvercharge_screen", cmd_screen, 2162),
    Function.ability(217, "Effect_PointDefenseDrone_screen", cmd_screen, 144),
    Function.ability(218, "Effect_PsiStorm_screen", cmd_screen, 1036),
    Function.ability(219, "Effect_PurificationNova_screen", cmd_screen, 2346),
    Function.ability(220, "Effect_Repair_screen", cmd_screen, 3685),
    Function.ability(221, "Effect_Repair_autocast", autocast, 3685),
    Function.ability(222, "Effect_Repair_Mule_screen", cmd_screen, 78, 3685),
    Function.ability(223, "Effect_Repair_Mule_autocast", autocast, 78, 3685),
    Function.ability(530, "Effect_Repair_RepairDrone_screen", cmd_screen, 3751, 3685),
    Function.ability(531, "Effect_Repair_RepairDrone_autocast", autocast, 3751, 3685),
    Function.ability(224, "Effect_Repair_SCV_screen", cmd_screen, 316, 3685),
    Function.ability(225, "Effect_Repair_SCV_autocast", autocast, 316, 3685),
    Function.ability(532, "Effect_RepairDrone_screen", cmd_screen, 3749),
    Function.ability(533, "Effect_Restore_screen", cmd_screen, 3765),
    Function.ability(534, "Effect_Restore_autocast", autocast, 3765),
    Function.ability(226, "Effect_Salvage_quick", cmd_quick, 32),
    Function.ability(227, "Effect_Scan_screen", cmd_screen, 399),
    Function.ability(542, "Effect_Scan_minimap", cmd_minimap, 399),
    Function.ability(228, "Effect_SpawnChangeling_quick", cmd_quick, 181),
    Function.ability(229, "Effect_SpawnLocusts_screen", cmd_screen, 2704),
    Function.ability(230, "Effect_Spray_screen", cmd_screen, 3684),
    Function.ability(231, "Effect_Spray_Protoss_screen", cmd_screen, 30, 3684),
    Function.ability(232, "Effect_Spray_Terran_screen", cmd_screen, 26, 3684),
    Function.ability(233, "Effect_Spray_Zerg_screen", cmd_screen, 28, 3684),
    Function.ability(549, "Effect_Spray_minimap", cmd_minimap, 3684),
    Function.ability(550, "Effect_Spray_Protoss_minimap", cmd_minimap, 30, 3684),
    Function.ability(551, "Effect_Spray_Terran_minimap", cmd_minimap, 26, 3684),
    Function.ability(552, "Effect_Spray_Zerg_minimap", cmd_minimap, 28, 3684),
    Function.ability(234, "Effect_Stim_quick", cmd_quick, 3675),
    Function.ability(235, "Effect_Stim_Marauder_quick", cmd_quick, 253, 3675),
    Function.ability(236, "Effect_Stim_Marauder_Redirect_quick", cmd_quick, 1684, 3675),
    Function.ability(237, "Effect_Stim_Marine_quick", cmd_quick, 380, 3675),
    Function.ability(238, "Effect_Stim_Marine_Redirect_quick", cmd_quick, 1683, 3675),
    Function.ability(239, "Effect_SupplyDrop_screen", cmd_screen, 255),
    Function.ability(240, "Effect_TacticalJump_screen", cmd_screen, 2358),
    Function.ability(553, "Effect_TacticalJump_minimap", cmd_minimap, 2358),
    Function.ability(241, "Effect_TimeWarp_screen", cmd_screen, 2244),
    Function.ability(242, "Effect_Transfusion_screen", cmd_screen, 1664),
    Function.ability(243, "Effect_ViperConsume_screen", cmd_screen, 2073),
    Function.ability(244, "Effect_VoidRayPrismaticAlignment_quick", cmd_quick, 2393),
    Function.ability(245, "Effect_WidowMineAttack_screen", cmd_screen, 2099),
    Function.ability(246, "Effect_WidowMineAttack_autocast", autocast, 2099),
    Function.ability(247, "Effect_YamatoGun_screen", cmd_screen, 401),
    Function.ability(248, "Hallucination_Adept_quick", cmd_quick, 2391),
    Function.ability(249, "Hallucination_Archon_quick", cmd_quick, 146),
    Function.ability(250, "Hallucination_Colossus_quick", cmd_quick, 148),
    Function.ability(251, "Hallucination_Disruptor_quick", cmd_quick, 2389),
    Function.ability(252, "Hallucination_HighTemplar_quick", cmd_quick, 150),
    Function.ability(253, "Hallucination_Immortal_quick", cmd_quick, 152),
    Function.ability(254, "Hallucination_Oracle_quick", cmd_quick, 2114),
    Function.ability(255, "Hallucination_Phoenix_quick", cmd_quick, 154),
    Function.ability(256, "Hallucination_Probe_quick", cmd_quick, 156),
    Function.ability(257, "Hallucination_Stalker_quick", cmd_quick, 158),
    Function.ability(258, "Hallucination_VoidRay_quick", cmd_quick, 160),
    Function.ability(259, "Hallucination_WarpPrism_quick", cmd_quick, 162),
    Function.ability(260, "Hallucination_Zealot_quick", cmd_quick, 164),
    Function.ability(261, "Halt_quick", cmd_quick, 3660),
    Function.ability(262, "Halt_Building_quick", cmd_quick, 315, 3660),
    Function.ability(263, "Halt_TerranBuild_quick", cmd_quick, 348, 3660),
    Function.ability(264, "Harvest_Gather_screen", cmd_screen, 3666),
    Function.ability(265, "Harvest_Gather_Drone_screen", cmd_screen, 1183, 3666),
    Function.ability(266, "Harvest_Gather_Mule_screen", cmd_screen, 166, 3666),
    Function.ability(267, "Harvest_Gather_Probe_screen", cmd_screen, 298, 3666),
    Function.ability(268, "Harvest_Gather_SCV_screen", cmd_screen, 295, 3666),
    Function.ability(269, "Harvest_Return_quick", cmd_quick, 3667),
    Function.ability(270, "Harvest_Return_Drone_quick", cmd_quick, 1184, 3667),
    Function.ability(271, "Harvest_Return_Mule_quick", cmd_quick, 167, 3667),
    Function.ability(272, "Harvest_Return_Probe_quick", cmd_quick, 299, 3667),
    Function.ability(273, "Harvest_Return_SCV_quick", cmd_quick, 296, 3667),
    Function.ability(274, "HoldPosition_quick", cmd_quick, 3793),
    Function.ability(558, "HoldPosition_Battlecruiser_quick", cmd_quick, 3778, 3793),
    Function.ability(559, "HoldPosition_Hold_quick", cmd_quick, 18, 3793),
    Function.ability(275, "Land_screen", cmd_screen, 3678),
    Function.ability(276, "Land_Barracks_screen", cmd_screen, 554, 3678),
    Function.ability(277, "Land_CommandCenter_screen", cmd_screen, 419, 3678),
    Function.ability(278, "Land_Factory_screen", cmd_screen, 520, 3678),
    Function.ability(279, "Land_OrbitalCommand_screen", cmd_screen, 1524, 3678),
    Function.ability(280, "Land_Starport_screen", cmd_screen, 522, 3678),
    Function.ability(281, "Lift_quick", cmd_quick, 3679),
    Function.ability(282, "Lift_Barracks_quick", cmd_quick, 452, 3679),
    Function.ability(283, "Lift_CommandCenter_quick", cmd_quick, 417, 3679),
    Function.ability(284, "Lift_Factory_quick", cmd_quick, 485, 3679),
    Function.ability(285, "Lift_OrbitalCommand_quick", cmd_quick, 1522, 3679),
    Function.ability(286, "Lift_Starport_quick", cmd_quick, 518, 3679),
    Function.ability(287, "Load_screen", cmd_screen, 3668),
    Function.ability(288, "Load_Bunker_screen", cmd_screen, 407, 3668),
    Function.ability(289, "Load_Medivac_screen", cmd_screen, 394, 3668),
    Function.ability(290, "Load_NydusNetwork_screen", cmd_screen, 1437, 3668),
    Function.ability(291, "Load_NydusWorm_screen", cmd_screen, 2370, 3668),
    Function.ability(292, "Load_Overlord_screen", cmd_screen, 1406, 3668),
    Function.ability(293, "Load_WarpPrism_screen", cmd_screen, 911, 3668),
    Function.ability(294, "LoadAll_quick", cmd_quick, 3663),
    Function.ability(295, "LoadAll_CommandCenter_quick", cmd_quick, 416, 3663),
    Function.ability(296, "Morph_Archon_quick", cmd_quick, 1766),
    Function.ability(297, "Morph_BroodLord_quick", cmd_quick, 1372),
    Function.ability(298, "Morph_Gateway_quick", cmd_quick, 1520),
    Function.ability(299, "Morph_GreaterSpire_quick", cmd_quick, 1220),
    Function.ability(300, "Morph_Hellbat_quick", cmd_quick, 1998),
    Function.ability(301, "Morph_Hellion_quick", cmd_quick, 1978),
    Function.ability(302, "Morph_Hive_quick", cmd_quick, 1218),
    Function.ability(303, "Morph_Lair_quick", cmd_quick, 1216),
    Function.ability(304, "Morph_LiberatorAAMode_quick", cmd_quick, 2560),
    Function.ability(305, "Morph_LiberatorAGMode_screen", cmd_screen, 2558),
    Function.ability(554, "Morph_LiberatorAGMode_minimap", cmd_minimap, 2558),
    Function.ability(306, "Morph_Lurker_quick", cmd_quick, 2332),
    Function.ability(307, "Morph_LurkerDen_quick", cmd_quick, 2112),
    Function.ability(308, "Morph_Mothership_quick", cmd_quick, 1847),
    Function.ability(535, "Morph_ObserverMode_quick", cmd_quick, 3739),
    Function.ability(309, "Morph_OrbitalCommand_quick", cmd_quick, 1516),
    Function.ability(310, "Morph_OverlordTransport_quick", cmd_quick, 2708),
    Function.ability(311, "Morph_Overseer_quick", cmd_quick, 1448),
    Function.ability(536, "Morph_OverseerMode_quick", cmd_quick, 3745),
    Function.ability(537, "Morph_OversightMode_quick", cmd_quick, 3743),
    Function.ability(312, "Morph_PlanetaryFortress_quick", cmd_quick, 1450),
    Function.ability(313, "Morph_Ravager_quick", cmd_quick, 2330),
    Function.ability(314, "Morph_Root_screen", cmd_screen, 3680),
    Function.ability(315, "Morph_SpineCrawlerRoot_screen", cmd_screen, 1729, 3680),
    Function.ability(316, "Morph_SporeCrawlerRoot_screen", cmd_screen, 1731, 3680),
    Function.ability(317, "Morph_SiegeMode_quick", cmd_quick, 388),
    Function.ability(318, "Morph_SupplyDepot_Lower_quick", cmd_quick, 556),
    Function.ability(319, "Morph_SupplyDepot_Raise_quick", cmd_quick, 558),
    Function.ability(538, "Morph_SurveillanceMode_quick", cmd_quick, 3741),
    Function.ability(320, "Morph_ThorExplosiveMode_quick", cmd_quick, 2364),
    Function.ability(321, "Morph_ThorHighImpactMode_quick", cmd_quick, 2362),
    Function.ability(322, "Morph_Unsiege_quick", cmd_quick, 390),
    Function.ability(323, "Morph_Uproot_quick", cmd_quick, 3681),
    Function.ability(324, "Morph_SpineCrawlerUproot_quick", cmd_quick, 1725, 3681),
    Function.ability(325, "Morph_SporeCrawlerUproot_quick", cmd_quick, 1727, 3681),
    Function.ability(326, "Morph_VikingAssaultMode_quick", cmd_quick, 403),
    Function.ability(327, "Morph_VikingFighterMode_quick", cmd_quick, 405),
    Function.ability(328, "Morph_WarpGate_quick", cmd_quick, 1518),
    Function.ability(560, "Morph_WarpGate_autocast", autocast, 1518),
    Function.ability(329, "Morph_WarpPrismPhasingMode_quick", cmd_quick, 1528),
    Function.ability(330, "Morph_WarpPrismTransportMode_quick", cmd_quick, 1530),
    Function.ability(331, "Move_screen", cmd_screen, 3794),
    Function.ability(332, "Move_minimap", cmd_minimap, 3794),
    Function.ability(561, "Move_Battlecruiser_screen", cmd_screen, 3776, 3794),
    Function.ability(562, "Move_Battlecruiser_minimap", cmd_minimap, 3776, 3794),
    Function.ability(563, "Move_Move_screen", cmd_screen, 16, 3794),
    Function.ability(564, "Move_Move_minimap", cmd_minimap, 16, 3794),
    Function.ability(333, "Patrol_screen", cmd_screen, 3795),
    Function.ability(334, "Patrol_minimap", cmd_minimap, 3795),
    Function.ability(565, "Patrol_Battlecruiser_screen", cmd_screen, 3777, 3795),
    Function.ability(566, "Patrol_Battlecruiser_minimap", cmd_minimap, 3777, 3795),
    Function.ability(567, "Patrol_Patrol_screen", cmd_screen, 17, 3795),
    Function.ability(568, "Patrol_Patrol_minimap", cmd_minimap, 17, 3795),
    Function.ability(335, "Rally_Units_screen", cmd_screen, 3673),
    Function.ability(336, "Rally_Units_minimap", cmd_minimap, 3673),
    Function.ability(337, "Rally_Building_screen", cmd_screen, 195, 3673),
    Function.ability(338, "Rally_Building_minimap", cmd_minimap, 195, 3673),
    Function.ability(339, "Rally_Hatchery_Units_screen", cmd_screen, 211, 3673),
    Function.ability(340, "Rally_Hatchery_Units_minimap", cmd_minimap, 211, 3673),
    Function.ability(341, "Rally_Morphing_Unit_screen", cmd_screen, 199, 3673),
    Function.ability(342, "Rally_Morphing_Unit_minimap", cmd_minimap, 199, 3673),
    Function.ability(343, "Rally_Workers_screen", cmd_screen, 3690),
    Function.ability(344, "Rally_Workers_minimap", cmd_minimap, 3690),
    Function.ability(345, "Rally_CommandCenter_screen", cmd_screen, 203, 3690),
    Function.ability(346, "Rally_CommandCenter_minimap", cmd_minimap, 203, 3690),
    Function.ability(347, "Rally_Hatchery_Workers_screen", cmd_screen, 212, 3690),
    Function.ability(348, "Rally_Hatchery_Workers_minimap", cmd_minimap, 212, 3690),
    Function.ability(349, "Rally_Nexus_screen", cmd_screen, 207, 3690),
    Function.ability(350, "Rally_Nexus_minimap", cmd_minimap, 207, 3690),
    Function.ability(539, "Research_AdaptiveTalons_quick", cmd_quick, 3709),
    Function.ability(351, "Research_AdeptResonatingGlaives_quick", cmd_quick, 1594),
    Function.ability(352, "Research_AdvancedBallistics_quick", cmd_quick, 805),
    Function.ability(569, "Research_AnabolicSynthesis_quick", cmd_quick, 263),
    Function.ability(353, "Research_BansheeCloakingField_quick", cmd_quick, 790),
    Function.ability(354, "Research_BansheeHyperflightRotors_quick", cmd_quick, 799),
    Function.ability(355, "Research_BattlecruiserWeaponRefit_quick", cmd_quick, 1532),
    Function.ability(356, "Research_Blink_quick", cmd_quick, 1593),
    Function.ability(357, "Research_Burrow_quick", cmd_quick, 1225),
    Function.ability(358, "Research_CentrifugalHooks_quick", cmd_quick, 1482),
    Function.ability(359, "Research_Charge_quick", cmd_quick, 1592),
    Function.ability(360, "Research_ChitinousPlating_quick", cmd_quick, 265),
    Function.ability(361, "Research_CombatShield_quick", cmd_quick, 731),
    Function.ability(362, "Research_ConcussiveShells_quick", cmd_quick, 732),
    Function.ability(570, "Research_CycloneLockOnDamage_quick", cmd_quick, 769),
    Function.ability(540, "Research_CycloneRapidFireLaunchers_quick", cmd_quick, 768),
    Function.ability(363, "Research_DrillingClaws_quick", cmd_quick, 764),
    Function.ability(572, "Research_EnhancedShockwaves_quick", cmd_quick, 822),
    Function.ability(364, "Research_ExtendedThermalLance_quick", cmd_quick, 1097),
    Function.ability(365, "Research_GlialRegeneration_quick", cmd_quick, 216),
    Function.ability(366, "Research_GraviticBooster_quick", cmd_quick, 1093),
    Function.ability(367, "Research_GraviticDrive_quick", cmd_quick, 1094),
    Function.ability(368, "Research_GroovedSpines_quick", cmd_quick, 1282),
    Function.ability(369, "Research_HiSecAutoTracking_quick", cmd_quick, 650),
    Function.ability(370, "Research_HighCapacityFuelTanks_quick", cmd_quick, 804),
    Function.ability(371, "Research_InfernalPreigniter_quick", cmd_quick, 761),
    Function.ability(372, "Research_InterceptorGravitonCatapult_quick", cmd_quick, 44),
    Function.ability(374, "Research_MuscularAugments_quick", cmd_quick, 1283),
    Function.ability(375, "Research_NeosteelFrame_quick", cmd_quick, 655),
    Function.ability(376, "Research_NeuralParasite_quick", cmd_quick, 1455),
    Function.ability(377, "Research_PathogenGlands_quick", cmd_quick, 1454),
    Function.ability(378, "Research_PersonalCloaking_quick", cmd_quick, 820),
    Function.ability(379, "Research_PhoenixAnionPulseCrystals_quick", cmd_quick, 46),
    Function.ability(380, "Research_PneumatizedCarapace_quick", cmd_quick, 1223),
    Function.ability(381, "Research_ProtossAirArmor_quick", cmd_quick, 3692),
    Function.ability(382, "Research_ProtossAirArmorLevel1_quick", cmd_quick, 1565, 3692),
    Function.ability(383, "Research_ProtossAirArmorLevel2_quick", cmd_quick, 1566, 3692),
    Function.ability(384, "Research_ProtossAirArmorLevel3_quick", cmd_quick, 1567, 3692),
    Function.ability(385, "Research_ProtossAirWeapons_quick", cmd_quick, 3693),
    Function.ability(386, "Research_ProtossAirWeaponsLevel1_quick", cmd_quick, 1562, 3693),
    Function.ability(387, "Research_ProtossAirWeaponsLevel2_quick", cmd_quick, 1563, 3693),
    Function.ability(388, "Research_ProtossAirWeaponsLevel3_quick", cmd_quick, 1564, 3693),
    Function.ability(389, "Research_ProtossGroundArmor_quick", cmd_quick, 3694),
    Function.ability(390, "Research_ProtossGroundArmorLevel1_quick", cmd_quick, 1065, 3694),
    Function.ability(391, "Research_ProtossGroundArmorLevel2_quick", cmd_quick, 1066, 3694),
    Function.ability(392, "Research_ProtossGroundArmorLevel3_quick", cmd_quick, 1067, 3694),
    Function.ability(393, "Research_ProtossGroundWeapons_quick", cmd_quick, 3695),
    Function.ability(394, "Research_ProtossGroundWeaponsLevel1_quick", cmd_quick, 1062, 3695),
    Function.ability(395, "Research_ProtossGroundWeaponsLevel2_quick", cmd_quick, 1063, 3695),
    Function.ability(396, "Research_ProtossGroundWeaponsLevel3_quick", cmd_quick, 1064, 3695),
    Function.ability(397, "Research_ProtossShields_quick", cmd_quick, 3696),
    Function.ability(398, "Research_ProtossShieldsLevel1_quick", cmd_quick, 1068, 3696),
    Function.ability(399, "Research_ProtossShieldsLevel2_quick", cmd_quick, 1069, 3696),
    Function.ability(400, "Research_ProtossShieldsLevel3_quick", cmd_quick, 1070, 3696),
    Function.ability(401, "Research_PsiStorm_quick", cmd_quick, 1126),
    Function.ability(402, "Research_RavenCorvidReactor_quick", cmd_quick, 793),
    Function.ability(403, "Research_RavenRecalibratedExplosives_quick", cmd_quick, 803),
    Function.ability(404, "Research_ShadowStrike_quick", cmd_quick, 2720),
    Function.ability(373, "Research_SmartServos_quick", cmd_quick, 766),
    Function.ability(405, "Research_Stimpack_quick", cmd_quick, 730),
    Function.ability(406, "Research_TerranInfantryArmor_quick", cmd_quick, 3697),
    Function.ability(407, "Research_TerranInfantryArmorLevel1_quick", cmd_quick, 656, 3697),
    Function.ability(408, "Research_TerranInfantryArmorLevel2_quick", cmd_quick, 657, 3697),
    Function.ability(409, "Research_TerranInfantryArmorLevel3_quick", cmd_quick, 658, 3697),
    Function.ability(410, "Research_TerranInfantryWeapons_quick", cmd_quick, 3698),
    Function.ability(411, "Research_TerranInfantryWeaponsLevel1_quick", cmd_quick, 652, 3698),
    Function.ability(412, "Research_TerranInfantryWeaponsLevel2_quick", cmd_quick, 653, 3698),
    Function.ability(413, "Research_TerranInfantryWeaponsLevel3_quick", cmd_quick, 654, 3698),
    Function.ability(414, "Research_TerranShipWeapons_quick", cmd_quick, 3699),
    Function.ability(415, "Research_TerranShipWeaponsLevel1_quick", cmd_quick, 861, 3699),
    Function.ability(416, "Research_TerranShipWeaponsLevel2_quick", cmd_quick, 862, 3699),
    Function.ability(417, "Research_TerranShipWeaponsLevel3_quick", cmd_quick, 863, 3699),
    Function.ability(418, "Research_TerranStructureArmorUpgrade_quick", cmd_quick, 651),
    Function.ability(419, "Research_TerranVehicleAndShipPlating_quick", cmd_quick, 3700),
    Function.ability(420, "Research_TerranVehicleAndShipPlatingLevel1_quick", cmd_quick, 864, 3700),
    Function.ability(421, "Research_TerranVehicleAndShipPlatingLevel2_quick", cmd_quick, 865, 3700),
    Function.ability(422, "Research_TerranVehicleAndShipPlatingLevel3_quick", cmd_quick, 866, 3700),
    Function.ability(423, "Research_TerranVehicleWeapons_quick", cmd_quick, 3701),
    Function.ability(424, "Research_TerranVehicleWeaponsLevel1_quick", cmd_quick, 855, 3701),
    Function.ability(425, "Research_TerranVehicleWeaponsLevel2_quick", cmd_quick, 856, 3701),
    Function.ability(426, "Research_TerranVehicleWeaponsLevel3_quick", cmd_quick, 857, 3701),
    Function.ability(427, "Research_TunnelingClaws_quick", cmd_quick, 217),
    Function.ability(428, "Research_WarpGate_quick", cmd_quick, 1568),
    Function.ability(429, "Research_ZergFlyerArmor_quick", cmd_quick, 3702),
    Function.ability(430, "Research_ZergFlyerArmorLevel1_quick", cmd_quick, 1315, 3702),
    Function.ability(431, "Research_ZergFlyerArmorLevel2_quick", cmd_quick, 1316, 3702),
    Function.ability(432, "Research_ZergFlyerArmorLevel3_quick", cmd_quick, 1317, 3702),
    Function.ability(433, "Research_ZergFlyerAttack_quick", cmd_quick, 3703),
    Function.ability(434, "Research_ZergFlyerAttackLevel1_quick", cmd_quick, 1312, 3703),
    Function.ability(435, "Research_ZergFlyerAttackLevel2_quick", cmd_quick, 1313, 3703),
    Function.ability(436, "Research_ZergFlyerAttackLevel3_quick", cmd_quick, 1314, 3703),
    Function.ability(437, "Research_ZergGroundArmor_quick", cmd_quick, 3704),
    Function.ability(438, "Research_ZergGroundArmorLevel1_quick", cmd_quick, 1189, 3704),
    Function.ability(439, "Research_ZergGroundArmorLevel2_quick", cmd_quick, 1190, 3704),
    Function.ability(440, "Research_ZergGroundArmorLevel3_quick", cmd_quick, 1191, 3704),
    Function.ability(441, "Research_ZergMeleeWeapons_quick", cmd_quick, 3705),
    Function.ability(442, "Research_ZergMeleeWeaponsLevel1_quick", cmd_quick, 1186, 3705),
    Function.ability(443, "Research_ZergMeleeWeaponsLevel2_quick", cmd_quick, 1187, 3705),
    Function.ability(444, "Research_ZergMeleeWeaponsLevel3_quick", cmd_quick, 1188, 3705),
    Function.ability(445, "Research_ZergMissileWeapons_quick", cmd_quick, 3706),
    Function.ability(446, "Research_ZergMissileWeaponsLevel1_quick", cmd_quick, 1192, 3706),
    Function.ability(447, "Research_ZergMissileWeaponsLevel2_quick", cmd_quick, 1193, 3706),
    Function.ability(448, "Research_ZergMissileWeaponsLevel3_quick", cmd_quick, 1194, 3706),
    Function.ability(449, "Research_ZerglingAdrenalGlands_quick", cmd_quick, 1252),
    Function.ability(450, "Research_ZerglingMetabolicBoost_quick", cmd_quick, 1253),
    Function.ability(451, "Smart_screen", cmd_screen, 1),
    Function.ability(452, "Smart_minimap", cmd_minimap, 1),
    Function.ability(453, "Stop_quick", cmd_quick, 3665),
    Function.ability(571, "Stop_Battlecruiser_quick", cmd_quick, 3783, 3665),
    Function.ability(454, "Stop_Building_quick", cmd_quick, 2057, 3665),
    Function.ability(455, "Stop_Redirect_quick", cmd_quick, 1691, 3665),
    Function.ability(456, "Stop_Stop_quick", cmd_quick, 4, 3665),
    Function.ability(457, "Train_Adept_quick", cmd_quick, 922),
    Function.ability(458, "Train_Baneling_quick", cmd_quick, 80),
    Function.ability(459, "Train_Banshee_quick", cmd_quick, 621),
    Function.ability(460, "Train_Battlecruiser_quick", cmd_quick, 623),
    Function.ability(461, "Train_Carrier_quick", cmd_quick, 948),
    Function.ability(462, "Train_Colossus_quick", cmd_quick, 978),
    Function.ability(463, "Train_Corruptor_quick", cmd_quick, 1353),
    Function.ability(464, "Train_Cyclone_quick", cmd_quick, 597),
    Function.ability(465, "Train_DarkTemplar_quick", cmd_quick, 920),
    Function.ability(466, "Train_Disruptor_quick", cmd_quick, 994),
    Function.ability(467, "Train_Drone_quick", cmd_quick, 1342),
    Function.ability(468, "Train_Ghost_quick", cmd_quick, 562),
    Function.ability(469, "Train_Hellbat_quick", cmd_quick, 596),
    Function.ability(470, "Train_Hellion_quick", cmd_quick, 595),
    Function.ability(471, "Train_HighTemplar_quick", cmd_quick, 919),
    Function.ability(472, "Train_Hydralisk_quick", cmd_quick, 1345),
    Function.ability(473, "Train_Immortal_quick", cmd_quick, 979),
    Function.ability(474, "Train_Infestor_quick", cmd_quick, 1352),
    Function.ability(475, "Train_Liberator_quick", cmd_quick, 626),
    Function.ability(476, "Train_Marauder_quick", cmd_quick, 563),
    Function.ability(477, "Train_Marine_quick", cmd_quick, 560),
    Function.ability(478, "Train_Medivac_quick", cmd_quick, 620),
    Function.ability(541, "Train_Mothership_quick", cmd_quick, 110),
    Function.ability(479, "Train_MothershipCore_quick", cmd_quick, 1853),
    Function.ability(480, "Train_Mutalisk_quick", cmd_quick, 1346),
    Function.ability(481, "Train_Observer_quick", cmd_quick, 977),
    Function.ability(482, "Train_Oracle_quick", cmd_quick, 954),
    Function.ability(483, "Train_Overlord_quick", cmd_quick, 1344),
    Function.ability(484, "Train_Phoenix_quick", cmd_quick, 946),
    Function.ability(485, "Train_Probe_quick", cmd_quick, 1006),
    Function.ability(486, "Train_Queen_quick", cmd_quick, 1632),
    Function.ability(487, "Train_Raven_quick", cmd_quick, 622),
    Function.ability(488, "Train_Reaper_quick", cmd_quick, 561),
    Function.ability(489, "Train_Roach_quick", cmd_quick, 1351),
    Function.ability(490, "Train_SCV_quick", cmd_quick, 524),
    Function.ability(491, "Train_Sentry_quick", cmd_quick, 921),
    Function.ability(492, "Train_SiegeTank_quick", cmd_quick, 591),
    Function.ability(493, "Train_Stalker_quick", cmd_quick, 917),
    Function.ability(494, "Train_SwarmHost_quick", cmd_quick, 1356),
    Function.ability(495, "Train_Tempest_quick", cmd_quick, 955),
    Function.ability(496, "Train_Thor_quick", cmd_quick, 594),
    Function.ability(497, "Train_Ultralisk_quick", cmd_quick, 1348),
    Function.ability(498, "Train_VikingFighter_quick", cmd_quick, 624),
    Function.ability(499, "Train_Viper_quick", cmd_quick, 1354),
    Function.ability(500, "Train_VoidRay_quick", cmd_quick, 950),
    Function.ability(501, "Train_WarpPrism_quick", cmd_quick, 976),
    Function.ability(502, "Train_WidowMine_quick", cmd_quick, 614),
    Function.ability(503, "Train_Zealot_quick", cmd_quick, 916),
    Function.ability(504, "Train_Zergling_quick", cmd_quick, 1343),
    Function.ability(505, "TrainWarp_Adept_screen", cmd_screen, 1419),
    Function.ability(506, "TrainWarp_DarkTemplar_screen", cmd_screen, 1417),
    Function.ability(507, "TrainWarp_HighTemplar_screen", cmd_screen, 1416),
    Function.ability(508, "TrainWarp_Sentry_screen", cmd_screen, 1418),
    Function.ability(509, "TrainWarp_Stalker_screen", cmd_screen, 1414),
    Function.ability(510, "TrainWarp_Zealot_screen", cmd_screen, 1413),
    Function.ability(511, "UnloadAll_quick", cmd_quick, 3664),
    Function.ability(512, "UnloadAll_Bunker_quick", cmd_quick, 408, 3664),
    Function.ability(513, "UnloadAll_CommandCenter_quick", cmd_quick, 413, 3664),
    Function.ability(514, "UnloadAll_NydusNetwork_quick", cmd_quick, 1438, 3664),
    Function.ability(515, "UnloadAll_NydusWorm_quick", cmd_quick, 2371, 3664),
    Function.ability(516, "UnloadAllAt_screen", cmd_screen, 3669),
    Function.ability(517, "UnloadAllAt_minimap", cmd_minimap, 3669),
    Function.ability(518, "UnloadAllAt_Medivac_screen", cmd_screen, 396, 3669),
    Function.ability(519, "UnloadAllAt_Medivac_minimap", cmd_minimap, 396, 3669),
    Function.ability(520, "UnloadAllAt_Overlord_screen", cmd_screen, 1408, 3669),
    Function.ability(521, "UnloadAllAt_Overlord_minimap", cmd_minimap, 1408, 3669),
    Function.ability(522, "UnloadAllAt_WarpPrism_screen", cmd_screen, 913, 3669),
    Function.ability(523, "UnloadAllAt_WarpPrism_minimap", cmd_minimap, 913, 3669),
]
# pylint: enable=line-too-long


# Create an IntEnum of the function names/ids so that printing the id will
# show something useful.
_Functions = enum.IntEnum(  # pylint: disable=invalid-name
    "_Functions", {f.name: f.id for f in _FUNCTIONS})
_FUNCTIONS = [f._replace(id=_Functions(f.id)) for f in _FUNCTIONS]
FUNCTIONS = Functions(_FUNCTIONS)

# Some indexes to support features.py and action conversion.
ABILITY_IDS = collections.defaultdict(set)  # {ability_id: {funcs}}
for _func in FUNCTIONS:
  if _func.ability_id >= 0:
    ABILITY_IDS[_func.ability_id].add(_func)
ABILITY_IDS = {k: frozenset(v) for k, v in ABILITY_IDS.items()}
FUNCTIONS_AVAILABLE = {f.id: f for f in FUNCTIONS if f.avail_fn}


# pylint: disable=line-too-long
_RAW_FUNCTIONS = [
    Function.raw_ui_func(0, "no_op", raw_no_op),
    Function.raw_ui_func(168, "raw_move_camera", raw_move_camera),
    Function.raw_ability(2, "Attack_pt", raw_cmd_pt, 3674),
    Function.raw_ability(3, "Attack_unit", raw_cmd_unit, 3674),
    Function.raw_ability(4, "Attack_Attack_pt", raw_cmd_pt, 23, 3674),
    Function.raw_ability(6, "Attack_AttackBuilding_pt", raw_cmd_pt, 2048, 3674),
    Function.raw_ability(5, "Attack_Attack_unit", raw_cmd_unit, 23, 3674),
    Function.raw_ability(7, "Attack_AttackBuilding_unit", raw_cmd_unit, 2048, 3674),
    Function.raw_ability(539, "Attack_Battlecruiser_pt", raw_cmd_pt, 3771, 3674),
    Function.raw_ability(540, "Attack_Battlecruiser_unit", raw_cmd_unit, 3771, 3674),
    Function.raw_ability(8, "Attack_Redirect_pt", raw_cmd_pt, 1682, 3674),
    Function.raw_ability(9, "Attack_Redirect_unit", raw_cmd_unit, 1682, 3674),
    Function.raw_ability(88, "Behavior_BuildingAttackOff_quick", raw_cmd, 2082),  # wrong / baneling
    Function.raw_ability(87, "Behavior_BuildingAttackOn_quick", raw_cmd, 2081),  # wrong / baneling
    Function.raw_ability(169, "Behavior_CloakOff_quick", raw_cmd, 3677),
    Function.raw_ability(170, "Behavior_CloakOff_Banshee_quick", raw_cmd, 393, 3677),
    Function.raw_ability(171, "Behavior_CloakOff_Ghost_quick", raw_cmd, 383, 3677),
    Function.raw_ability(172, "Behavior_CloakOn_quick", raw_cmd, 3676),
    Function.raw_ability(173, "Behavior_CloakOn_Banshee_quick", raw_cmd, 392, 3676),
    Function.raw_ability(174, "Behavior_CloakOn_Ghost_quick", raw_cmd, 382, 3676),
    Function.raw_ability(175, "Behavior_GenerateCreepOff_quick", raw_cmd, 1693),
    Function.raw_ability(176, "Behavior_GenerateCreepOn_quick", raw_cmd, 1692),
    Function.raw_ability(178, "Behavior_HoldFireOff_Ghost_quick", raw_cmd, 38, 3689),
    Function.raw_ability(179, "Behavior_HoldFireOff_Lurker_quick", raw_cmd, 2552, 3689),
    Function.raw_ability(177, "Behavior_HoldFireOff_quick", raw_cmd, 3689),
    Function.raw_ability(181, "Behavior_HoldFireOn_Ghost_quick", raw_cmd, 36, 3688),
    Function.raw_ability(182, "Behavior_HoldFireOn_Lurker_quick", raw_cmd, 2550, 3688),
    Function.raw_ability(180, "Behavior_HoldFireOn_quick", raw_cmd, 3688),
    Function.raw_ability(158, "Behavior_PulsarBeamOff_quick", raw_cmd, 2376),
    Function.raw_ability(159, "Behavior_PulsarBeamOn_quick", raw_cmd, 2375),
    Function.raw_ability(183, "Build_Armory_pt", raw_cmd_pt, 331),
    Function.raw_ability(36, "Build_Assimilator_unit", raw_cmd_unit, 882),
    Function.raw_ability(184, "Build_BanelingNest_pt", raw_cmd_pt, 1162),
    Function.raw_ability(185, "Build_Barracks_pt", raw_cmd_pt, 321),
    Function.raw_ability(186, "Build_Bunker_pt", raw_cmd_pt, 324),
    Function.raw_ability(187, "Build_CommandCenter_pt", raw_cmd_pt, 318),
    Function.raw_ability(188, "Build_CreepTumor_pt", raw_cmd_pt, 3691),
    Function.raw_ability(189, "Build_CreepTumor_Queen_pt", raw_cmd_pt, 1694, 3691),
    Function.raw_ability(190, "Build_CreepTumor_Tumor_pt", raw_cmd_pt, 1733, 3691),
    Function.raw_ability(47, "Build_CyberneticsCore_pt", raw_cmd_pt, 894),
    Function.raw_ability(44, "Build_DarkShrine_pt", raw_cmd_pt, 891),
    Function.raw_ability(191, "Build_EngineeringBay_pt", raw_cmd_pt, 322),
    Function.raw_ability(192, "Build_EvolutionChamber_pt", raw_cmd_pt, 1156),
    Function.raw_ability(193, "Build_Extractor_unit", raw_cmd_unit, 1154),
    Function.raw_ability(194, "Build_Factory_pt", raw_cmd_pt, 328),
    Function.raw_ability(39, "Build_FleetBeacon_pt", raw_cmd_pt, 885),
    Function.raw_ability(38, "Build_Forge_pt", raw_cmd_pt, 884),
    Function.raw_ability(195, "Build_FusionCore_pt", raw_cmd_pt, 333),
    Function.raw_ability(37, "Build_Gateway_pt", raw_cmd_pt, 883),
    Function.raw_ability(196, "Build_GhostAcademy_pt", raw_cmd_pt, 327),
    Function.raw_ability(197, "Build_Hatchery_pt", raw_cmd_pt, 1152),
    Function.raw_ability(198, "Build_HydraliskDen_pt", raw_cmd_pt, 1157),
    Function.raw_ability(199, "Build_InfestationPit_pt", raw_cmd_pt, 1160),
    Function.raw_ability(200, "Build_Interceptors_autocast", raw_autocast, 1042),
    Function.raw_ability(66, "Build_Interceptors_quick", raw_cmd, 1042),
    Function.raw_ability(201, "Build_LurkerDen_pt", raw_cmd_pt, 1163),
    Function.raw_ability(202, "Build_MissileTurret_pt", raw_cmd_pt, 323),
    Function.raw_ability(34, "Build_Nexus_pt", raw_cmd_pt, 880),
    Function.raw_ability(203, "Build_Nuke_quick", raw_cmd, 710),
    Function.raw_ability(204, "Build_NydusNetwork_pt", raw_cmd_pt, 1161),
    Function.raw_ability(205, "Build_NydusWorm_pt", raw_cmd_pt, 1768),
    Function.raw_ability(41, "Build_PhotonCannon_pt", raw_cmd_pt, 887),
    Function.raw_ability(35, "Build_Pylon_pt", raw_cmd_pt, 881),
    Function.raw_ability(207, "Build_Reactor_pt", raw_cmd_pt, 3683),
    Function.raw_ability(206, "Build_Reactor_quick", raw_cmd, 3683),
    Function.raw_ability(209, "Build_Reactor_Barracks_pt", raw_cmd_pt, 422, 3683),
    Function.raw_ability(208, "Build_Reactor_Barracks_quick", raw_cmd, 422, 3683),
    Function.raw_ability(211, "Build_Reactor_Factory_pt", raw_cmd_pt, 455, 3683),
    Function.raw_ability(210, "Build_Reactor_Factory_quick", raw_cmd, 455, 3683),
    Function.raw_ability(213, "Build_Reactor_Starport_pt", raw_cmd_pt, 488, 3683),
    Function.raw_ability(212, "Build_Reactor_Starport_quick", raw_cmd, 488, 3683),
    Function.raw_ability(214, "Build_Refinery_pt", raw_cmd_unit, 320),
    Function.raw_ability(215, "Build_RoachWarren_pt", raw_cmd_pt, 1165),
    Function.raw_ability(45, "Build_RoboticsBay_pt", raw_cmd_pt, 892),
    Function.raw_ability(46, "Build_RoboticsFacility_pt", raw_cmd_pt, 893),
    Function.raw_ability(216, "Build_SensorTower_pt", raw_cmd_pt, 326),
    Function.raw_ability(48, "Build_ShieldBattery_pt", raw_cmd_pt, 895),
    Function.raw_ability(217, "Build_SpawningPool_pt", raw_cmd_pt, 1155),
    Function.raw_ability(218, "Build_SpineCrawler_pt", raw_cmd_pt, 1166),
    Function.raw_ability(219, "Build_Spire_pt", raw_cmd_pt, 1158),
    Function.raw_ability(220, "Build_SporeCrawler_pt", raw_cmd_pt, 1167),
    Function.raw_ability(42, "Build_Stargate_pt", raw_cmd_pt, 889),
    Function.raw_ability(221, "Build_Starport_pt", raw_cmd_pt, 329),
    Function.raw_ability(95, "Build_StasisTrap_pt", raw_cmd_pt, 2505),
    Function.raw_ability(222, "Build_SupplyDepot_pt", raw_cmd_pt, 319),
    Function.raw_ability(224, "Build_TechLab_pt", raw_cmd_pt, 3682),
    Function.raw_ability(223, "Build_TechLab_quick", raw_cmd, 3682),
    Function.raw_ability(226, "Build_TechLab_Barracks_pt", raw_cmd_pt, 421, 3682),
    Function.raw_ability(225, "Build_TechLab_Barracks_quick", raw_cmd, 421, 3682),
    Function.raw_ability(228, "Build_TechLab_Factory_pt", raw_cmd_pt, 454, 3682),
    Function.raw_ability(227, "Build_TechLab_Factory_quick", raw_cmd, 454, 3682),
    Function.raw_ability(230, "Build_TechLab_Starport_pt", raw_cmd_pt, 487, 3682),
    Function.raw_ability(229, "Build_TechLab_Starport_quick", raw_cmd, 487, 3682),
    Function.raw_ability(43, "Build_TemplarArchive_pt", raw_cmd_pt, 890),
    Function.raw_ability(40, "Build_TwilightCouncil_pt", raw_cmd_pt, 886),
    Function.raw_ability(231, "Build_UltraliskCavern_pt", raw_cmd_pt, 1159),
    Function.raw_ability(232, "BurrowDown_quick", raw_cmd, 3661),
    Function.raw_ability(233, "BurrowDown_Baneling_quick", raw_cmd, 1374, 3661),
    Function.raw_ability(234, "BurrowDown_Drone_quick", raw_cmd, 1378, 3661),
    Function.raw_ability(235, "BurrowDown_Hydralisk_quick", raw_cmd, 1382, 3661),
    Function.raw_ability(236, "BurrowDown_Infestor_quick", raw_cmd, 1444, 3661),
    Function.raw_ability(237, "BurrowDown_InfestorTerran_quick", raw_cmd, 1394, 3661),
    Function.raw_ability(238, "BurrowDown_Lurker_quick", raw_cmd, 2108, 3661),
    Function.raw_ability(239, "BurrowDown_Queen_quick", raw_cmd, 1433, 3661),
    Function.raw_ability(240, "BurrowDown_Ravager_quick", raw_cmd, 2340, 3661),
    Function.raw_ability(241, "BurrowDown_Roach_quick", raw_cmd, 1386, 3661),
    Function.raw_ability(242, "BurrowDown_SwarmHost_quick", raw_cmd, 2014, 3661),
    Function.raw_ability(243, "BurrowDown_Ultralisk_quick", raw_cmd, 1512, 3661),
    Function.raw_ability(244, "BurrowDown_WidowMine_quick", raw_cmd, 2095, 3661),
    Function.raw_ability(245, "BurrowDown_Zergling_quick", raw_cmd, 1390, 3661),
    Function.raw_ability(247, "BurrowUp_autocast", raw_autocast, 3662),
    Function.raw_ability(246, "BurrowUp_quick", raw_cmd, 3662),
    Function.raw_ability(249, "BurrowUp_Baneling_autocast", raw_autocast, 1376, 3662),
    Function.raw_ability(248, "BurrowUp_Baneling_quick", raw_cmd, 1376, 3662),
    Function.raw_ability(250, "BurrowUp_Drone_quick", raw_cmd, 1380, 3662),
    Function.raw_ability(252, "BurrowUp_Hydralisk_autocast", raw_autocast, 1384, 3662),
    Function.raw_ability(251, "BurrowUp_Hydralisk_quick", raw_cmd, 1384, 3662),
    Function.raw_ability(253, "BurrowUp_Infestor_quick", raw_cmd, 1446, 3662),
    Function.raw_ability(255, "BurrowUp_InfestorTerran_autocast", raw_autocast, 1396, 3662),
    Function.raw_ability(254, "BurrowUp_InfestorTerran_quick", raw_cmd, 1396, 3662),
    Function.raw_ability(256, "BurrowUp_Lurker_quick", raw_cmd, 2110, 3662),
    Function.raw_ability(258, "BurrowUp_Queen_autocast", raw_autocast, 1435, 3662),
    Function.raw_ability(257, "BurrowUp_Queen_quick", raw_cmd, 1435, 3662),
    Function.raw_ability(260, "BurrowUp_Ravager_autocast", raw_autocast, 2342, 3662),
    Function.raw_ability(259, "BurrowUp_Ravager_quick", raw_cmd, 2342, 3662),
    Function.raw_ability(262, "BurrowUp_Roach_autocast", raw_autocast, 1388, 3662),
    Function.raw_ability(261, "BurrowUp_Roach_quick", raw_cmd, 1388, 3662),
    Function.raw_ability(263, "BurrowUp_SwarmHost_quick", raw_cmd, 2016, 3662),
    Function.raw_ability(265, "BurrowUp_Ultralisk_autocast", raw_autocast, 1514, 3662),
    Function.raw_ability(264, "BurrowUp_Ultralisk_quick", raw_cmd, 1514, 3662),
    Function.raw_ability(266, "BurrowUp_WidowMine_quick", raw_cmd, 2097, 3662),
    Function.raw_ability(268, "BurrowUp_Zergling_autocast", raw_autocast, 1392, 3662),
    Function.raw_ability(267, "BurrowUp_Zergling_quick", raw_cmd, 1392, 3662),
    Function.raw_ability(98, "Cancel_quick", raw_cmd, 3659),
    Function.raw_ability(123, "Cancel_AdeptPhaseShift_quick", raw_cmd, 2594, 3659),
    Function.raw_ability(124, "Cancel_AdeptShadePhaseShift_quick", raw_cmd, 2596, 3659),
    Function.raw_ability(269, "Cancel_BarracksAddOn_quick", raw_cmd, 451, 3659),
    Function.raw_ability(125, "Cancel_BuildInProgress_quick", raw_cmd, 314, 3659),
    Function.raw_ability(270, "Cancel_CreepTumor_quick", raw_cmd, 1763, 3659),
    Function.raw_ability(271, "Cancel_FactoryAddOn_quick", raw_cmd, 484, 3659),
    Function.raw_ability(126, "Cancel_GravitonBeam_quick", raw_cmd, 174, 3659),
    Function.raw_ability(272, "Cancel_HangarQueue5_quick", raw_cmd, 1038, 3671),
    Function.raw_ability(129, "Cancel_Last_quick", raw_cmd, 3671),
    Function.raw_ability(273, "Cancel_LockOn_quick", raw_cmd, 2354, 3659),
    Function.raw_ability(274, "Cancel_MorphBroodlord_quick", raw_cmd, 1373, 3659),
    Function.raw_ability(275, "Cancel_MorphGreaterSpire_quick", raw_cmd, 1221, 3659),
    Function.raw_ability(276, "Cancel_MorphHive_quick", raw_cmd, 1219, 3659),
    Function.raw_ability(277, "Cancel_MorphLair_quick", raw_cmd, 1217, 3659),
    Function.raw_ability(279, "Cancel_MorphLurkerDen_quick", raw_cmd, 2113, 3659),
    Function.raw_ability(278, "Cancel_MorphLurker_quick", raw_cmd, 2333, 3659),
    Function.raw_ability(280, "Cancel_MorphMothership_quick", raw_cmd, 1848, 3659),
    Function.raw_ability(281, "Cancel_MorphOrbital_quick", raw_cmd, 1517, 3659),
    Function.raw_ability(282, "Cancel_MorphOverlordTransport_quick", raw_cmd, 2709, 3659),
    Function.raw_ability(283, "Cancel_MorphOverseer_quick", raw_cmd, 1449, 3659),
    Function.raw_ability(284, "Cancel_MorphPlanetaryFortress_quick", raw_cmd, 1451, 3659),
    Function.raw_ability(285, "Cancel_MorphRavager_quick", raw_cmd, 2331, 3659),
    Function.raw_ability(286, "Cancel_MorphThorExplosiveMode_quick", raw_cmd, 2365, 3659),
    Function.raw_ability(287, "Cancel_NeuralParasite_quick", raw_cmd, 250, 3659),
    Function.raw_ability(288, "Cancel_Nuke_quick", raw_cmd, 1623, 3659),
    Function.raw_ability(130, "Cancel_Queue1_quick", raw_cmd, 304, 3671),
    Function.raw_ability(131, "Cancel_Queue5_quick", raw_cmd, 306, 3671),
    Function.raw_ability(289, "Cancel_QueueAddOn_quick", raw_cmd, 312, 3671),
    Function.raw_ability(132, "Cancel_QueueCancelToSelection_quick", raw_cmd, 308, 3671),
    Function.raw_ability(134, "Cancel_QueuePassiveCancelToSelection_quick", raw_cmd, 1833, 3671),
    Function.raw_ability(133, "Cancel_QueuePassive_quick", raw_cmd, 1831, 3671),
    Function.raw_ability(290, "Cancel_SpineCrawlerRoot_quick", raw_cmd, 1730, 3659),
    Function.raw_ability(291, "Cancel_SporeCrawlerRoot_quick", raw_cmd, 1732, 3659),
    Function.raw_ability(292, "Cancel_StarportAddOn_quick", raw_cmd, 517, 3659),
    Function.raw_ability(127, "Cancel_StasisTrap_quick", raw_cmd, 2535, 3659),
    Function.raw_ability(128, "Cancel_VoidRayPrismaticAlignment_quick", raw_cmd, 3707, 3659),
    Function.raw_ability(293, "Effect_Abduct_unit", raw_cmd_unit, 2067),
    Function.raw_ability(96, "Effect_AdeptPhaseShift_pt", raw_cmd_pt, 2544),
    Function.raw_ability(294, "Effect_AntiArmorMissile_unit", raw_cmd_unit, 3753),
    Function.raw_ability(295, "Effect_AutoTurret_pt", raw_cmd_pt, 1764),
    Function.raw_ability(296, "Effect_BlindingCloud_pt", raw_cmd_pt, 2063),
    Function.raw_ability(111, "Effect_Blink_pt", raw_cmd_pt, 3687),
    Function.raw_ability(135, "Effect_Blink_Stalker_pt", raw_cmd_pt, 1442, 3687),
    Function.raw_ability(112, "Effect_Blink_unit", raw_cmd_unit, 3687),  # wrong/unit
    Function.raw_ability(297, "Effect_CalldownMULE_pt", raw_cmd_pt, 171),
    Function.raw_ability(298, "Effect_CalldownMULE_unit", raw_cmd_unit, 171),
    Function.raw_ability(299, "Effect_CausticSpray_unit", raw_cmd_unit, 2324),
    Function.raw_ability(302, "Effect_Charge_autocast", raw_autocast, 1819),
    Function.raw_ability(300, "Effect_Charge_pt", raw_cmd_pt, 1819),
    Function.raw_ability(301, "Effect_Charge_unit", raw_cmd_unit, 1819),
    Function.raw_ability(122, "Effect_ChronoBoostEnergyCost_unit", raw_cmd_unit, 3755),  # new 4.0?
    Function.raw_ability(33, "Effect_ChronoBoost_unit", raw_cmd_unit, 261),  # wrong / old?
    Function.raw_ability(303, "Effect_Contaminate_unit", raw_cmd_unit, 1825),
    Function.raw_ability(304, "Effect_CorrosiveBile_pt", raw_cmd_pt, 2338),
    Function.raw_ability(305, "Effect_EMP_pt", raw_cmd_pt, 1628),
    Function.raw_ability(306, "Effect_EMP_unit", raw_cmd_unit, 1628),
    Function.raw_ability(307, "Effect_Explode_quick", raw_cmd, 42),
    Function.raw_ability(157, "Effect_Feedback_unit", raw_cmd_unit, 140),
    Function.raw_ability(79, "Effect_ForceField_pt", raw_cmd_pt, 1526),
    Function.raw_ability(308, "Effect_FungalGrowth_pt", raw_cmd_pt, 74),
    Function.raw_ability(309, "Effect_FungalGrowth_unit", raw_cmd_unit, 74),
    Function.raw_ability(310, "Effect_GhostSnipe_unit", raw_cmd_unit, 2714),
    Function.raw_ability(32, "Effect_GravitonBeam_unit", raw_cmd_unit, 173),
    Function.raw_ability(20, "Effect_GuardianShield_quick", raw_cmd, 76),
    Function.raw_ability(312, "Effect_Heal_autocast", raw_autocast, 386),
    Function.raw_ability(311, "Effect_Heal_unit", raw_cmd_unit, 386),
    Function.raw_ability(313, "Effect_ImmortalBarrier_autocast", raw_autocast, 2328),
    Function.raw_ability(91, "Effect_ImmortalBarrier_quick", raw_cmd, 2328),
    Function.raw_ability(314, "Effect_InfestedTerrans_pt", raw_cmd_pt, 247),
    Function.raw_ability(315, "Effect_InjectLarva_unit", raw_cmd_unit, 251),
    Function.raw_ability(316, "Effect_InterferenceMatrix_unit", raw_cmd_unit, 3747),
    Function.raw_ability(317, "Effect_KD8Charge_pt", raw_cmd_pt, 2588),
    Function.raw_ability(538, "Effect_KD8Charge_unit", raw_cmd_unit, 2588),
    Function.raw_ability(318, "Effect_LockOn_unit", raw_cmd_unit, 2350),
    Function.raw_ability(541, "Effect_LockOn_autocast", raw_autocast, 2350),
    Function.raw_ability(319, "Effect_LocustSwoop_pt", raw_cmd_pt, 2387),
    Function.raw_ability(110, "Effect_MassRecall_pt", raw_cmd_pt, 3686),
    Function.raw_ability(136, "Effect_MassRecall_Mothership_pt", raw_cmd_pt, 2368, 3686),
    Function.raw_ability(162, "Effect_MassRecall_Nexus_pt", raw_cmd_pt, 3757, 3686),
    Function.raw_ability(137, "Effect_MassRecall_StrategicRecall_pt", raw_cmd_pt, 142, 3686),
    Function.raw_ability(320, "Effect_MedivacIgniteAfterburners_quick", raw_cmd, 2116),
    Function.raw_ability(321, "Effect_NeuralParasite_unit", raw_cmd_unit, 249),
    Function.raw_ability(322, "Effect_NukeCalldown_pt", raw_cmd_pt, 1622),
    Function.raw_ability(90, "Effect_OracleRevelation_pt", raw_cmd_pt, 2146),
    Function.raw_ability(323, "Effect_ParasiticBomb_unit", raw_cmd_unit, 2542),
    Function.raw_ability(65, "Effect_PsiStorm_pt", raw_cmd_pt, 1036),
    Function.raw_ability(167, "Effect_PurificationNova_pt", raw_cmd_pt, 2346),
    Function.raw_ability(324, "Effect_Repair_autocast", raw_autocast, 3685),
    Function.raw_ability(108, "Effect_Repair_pt", raw_cmd_pt, 3685),
    Function.raw_ability(109, "Effect_Repair_unit", raw_cmd_unit, 3685),
    Function.raw_ability(326, "Effect_Repair_Mule_autocast", raw_autocast, 78, 3685),
    Function.raw_ability(325, "Effect_Repair_Mule_unit", raw_cmd_unit, 78, 3685),
    Function.raw_ability(328, "Effect_Repair_RepairDrone_autocast", raw_autocast, 3751, 3685),
    Function.raw_ability(327, "Effect_Repair_RepairDrone_unit", raw_cmd_unit, 3751, 3685),
    Function.raw_ability(330, "Effect_Repair_SCV_autocast", raw_autocast, 316, 3685),
    Function.raw_ability(329, "Effect_Repair_SCV_unit", raw_cmd_unit, 316, 3685),
    Function.raw_ability(331, "Effect_Restore_autocast", raw_autocast, 3765),
    Function.raw_ability(161, "Effect_Restore_unit", raw_cmd_unit, 3765),
    Function.raw_ability(332, "Effect_Salvage_quick", raw_cmd, 32),
    Function.raw_ability(333, "Effect_Scan_pt", raw_cmd_pt, 399),
    Function.raw_ability(113, "Effect_ShadowStride_pt", raw_cmd_pt, 2700, 3687),
    Function.raw_ability(334, "Effect_SpawnChangeling_quick", raw_cmd, 181),
    Function.raw_ability(335, "Effect_SpawnLocusts_pt", raw_cmd_pt, 2704),
    Function.raw_ability(336, "Effect_SpawnLocusts_unit", raw_cmd_unit, 2704),
    Function.raw_ability(337, "Effect_Spray_pt", raw_cmd_pt, 3684),
    Function.raw_ability(338, "Effect_Spray_Protoss_pt", raw_cmd_pt, 30, 3684),
    Function.raw_ability(339, "Effect_Spray_Terran_pt", raw_cmd_pt, 26, 3684),
    Function.raw_ability(340, "Effect_Spray_Zerg_pt", raw_cmd_pt, 28, 3684),
    Function.raw_ability(341, "Effect_Stim_quick", raw_cmd, 3675),
    Function.raw_ability(342, "Effect_Stim_Marauder_quick", raw_cmd, 253, 3675),
    Function.raw_ability(343, "Effect_Stim_Marauder_Redirect_quick", raw_cmd, 1684, 3675),
    Function.raw_ability(344, "Effect_Stim_Marine_quick", raw_cmd, 380, 3675),
    Function.raw_ability(345, "Effect_Stim_Marine_Redirect_quick", raw_cmd, 1683, 3675),
    Function.raw_ability(346, "Effect_SupplyDrop_unit", raw_cmd_unit, 255),
    Function.raw_ability(347, "Effect_TacticalJump_pt", raw_cmd_pt, 2358),
    Function.raw_ability(348, "Effect_TimeWarp_pt", raw_cmd_pt, 2244),
    Function.raw_ability(349, "Effect_Transfusion_unit", raw_cmd_unit, 1664),
    Function.raw_ability(350, "Effect_ViperConsume_unit", raw_cmd_unit, 2073),
    Function.raw_ability(94, "Effect_VoidRayPrismaticAlignment_quick", raw_cmd, 2393),
    Function.raw_ability(353, "Effect_WidowMineAttack_autocast", raw_autocast, 2099),
    Function.raw_ability(351, "Effect_WidowMineAttack_pt", raw_cmd_pt, 2099),
    Function.raw_ability(352, "Effect_WidowMineAttack_unit", raw_cmd_unit, 2099),
    Function.raw_ability(537, "Effect_YamatoGun_unit", raw_cmd_unit, 401),
    Function.raw_ability(93, "Hallucination_Adept_quick", raw_cmd, 2391),
    Function.raw_ability(22, "Hallucination_Archon_quick", raw_cmd, 146),
    Function.raw_ability(23, "Hallucination_Colossus_quick", raw_cmd, 148),
    Function.raw_ability(92, "Hallucination_Disruptor_quick", raw_cmd, 2389),
    Function.raw_ability(24, "Hallucination_HighTemplar_quick", raw_cmd, 150),
    Function.raw_ability(25, "Hallucination_Immortal_quick", raw_cmd, 152),
    Function.raw_ability(89, "Hallucination_Oracle_quick", raw_cmd, 2114),
    Function.raw_ability(26, "Hallucination_Phoenix_quick", raw_cmd, 154),
    Function.raw_ability(27, "Hallucination_Probe_quick", raw_cmd, 156),
    Function.raw_ability(28, "Hallucination_Stalker_quick", raw_cmd, 158),
    Function.raw_ability(29, "Hallucination_VoidRay_quick", raw_cmd, 160),
    Function.raw_ability(30, "Hallucination_WarpPrism_quick", raw_cmd, 162),
    Function.raw_ability(31, "Hallucination_Zealot_quick", raw_cmd, 164),
    Function.raw_ability(354, "Halt_Building_quick", raw_cmd, 315, 3660),
    Function.raw_ability(99, "Halt_quick", raw_cmd, 3660),
    Function.raw_ability(355, "Halt_TerranBuild_quick", raw_cmd, 348, 3660),
    Function.raw_ability(102, "Harvest_Gather_unit", raw_cmd_unit, 3666),
    Function.raw_ability(356, "Harvest_Gather_Drone_unit", raw_cmd_unit, 1183, 3666),
    Function.raw_ability(357, "Harvest_Gather_Mule_unit", raw_cmd_unit, 166, 3666),
    Function.raw_ability(358, "Harvest_Gather_Probe_unit", raw_cmd_unit, 298, 3666),
    Function.raw_ability(359, "Harvest_Gather_SCV_unit", raw_cmd_unit, 295, 3666),
    Function.raw_ability(103, "Harvest_Return_quick", raw_cmd, 3667),
    Function.raw_ability(360, "Harvest_Return_Drone_quick", raw_cmd, 1184, 3667),
    Function.raw_ability(361, "Harvest_Return_Mule_quick", raw_cmd, 167, 3667),
    Function.raw_ability(154, "Harvest_Return_Probe_quick", raw_cmd, 299, 3667),
    Function.raw_ability(362, "Harvest_Return_SCV_quick", raw_cmd, 296, 3667),
    Function.raw_ability(17, "HoldPosition_quick", raw_cmd, 3793),
    Function.raw_ability(542, "HoldPosition_Battlecruiser_quick", raw_cmd, 3778, 3793),
    Function.raw_ability(543, "HoldPosition_Hold_quick", raw_cmd, 18, 3793),
    Function.raw_ability(364, "Land_Barracks_pt", raw_cmd_pt, 554, 3678),
    Function.raw_ability(365, "Land_CommandCenter_pt", raw_cmd_pt, 419, 3678),
    Function.raw_ability(366, "Land_Factory_pt", raw_cmd_pt, 520, 3678),
    Function.raw_ability(367, "Land_OrbitalCommand_pt", raw_cmd_pt, 1524, 3678),
    Function.raw_ability(363, "Land_pt", raw_cmd_pt, 3678),
    Function.raw_ability(368, "Land_Starport_pt", raw_cmd_pt, 522, 3678),
    Function.raw_ability(370, "Lift_Barracks_quick", raw_cmd, 452, 3679),
    Function.raw_ability(371, "Lift_CommandCenter_quick", raw_cmd, 417, 3679),
    Function.raw_ability(372, "Lift_Factory_quick", raw_cmd, 485, 3679),
    Function.raw_ability(373, "Lift_OrbitalCommand_quick", raw_cmd, 1522, 3679),
    Function.raw_ability(369, "Lift_quick", raw_cmd, 3679),
    Function.raw_ability(374, "Lift_Starport_quick", raw_cmd, 518, 3679),
    Function.raw_ability(376, "LoadAll_CommandCenter_quick", raw_cmd, 416, 3663),
    Function.raw_ability(375, "LoadAll_quick", raw_cmd, 3663),
    Function.raw_ability(377, "Load_Bunker_unit", raw_cmd_unit, 407, 3668),
    Function.raw_ability(378, "Load_Medivac_unit", raw_cmd_unit, 394, 3668),
    Function.raw_ability(379, "Load_NydusNetwork_unit", raw_cmd_unit, 1437, 3668),
    Function.raw_ability(380, "Load_NydusWorm_unit", raw_cmd_unit, 2370, 3668),
    Function.raw_ability(381, "Load_Overlord_unit", raw_cmd_unit, 1406, 3668),
    Function.raw_ability(104, "Load_unit", raw_cmd_unit, 3668),
    Function.raw_ability(382, "Load_WarpPrism_unit", raw_cmd_unit, 911, 3668),
    Function.raw_ability(86, "Morph_Archon_quick", raw_cmd, 1766),
    Function.raw_ability(383, "Morph_BroodLord_quick", raw_cmd, 1372),
    Function.raw_ability(78, "Morph_Gateway_quick", raw_cmd, 1520),
    Function.raw_ability(384, "Morph_GreaterSpire_quick", raw_cmd, 1220),
    Function.raw_ability(385, "Morph_Hellbat_quick", raw_cmd, 1998),
    Function.raw_ability(386, "Morph_Hellion_quick", raw_cmd, 1978),
    Function.raw_ability(387, "Morph_Hive_quick", raw_cmd, 1218),
    Function.raw_ability(388, "Morph_Lair_quick", raw_cmd, 1216),
    Function.raw_ability(389, "Morph_LiberatorAAMode_quick", raw_cmd, 2560),
    Function.raw_ability(390, "Morph_LiberatorAGMode_pt", raw_cmd_pt, 2558),
    Function.raw_ability(392, "Morph_LurkerDen_quick", raw_cmd, 2112),
    Function.raw_ability(391, "Morph_Lurker_quick", raw_cmd, 2332),
    Function.raw_ability(393, "Morph_Mothership_quick", raw_cmd, 1847),
    Function.raw_ability(121, "Morph_ObserverMode_quick", raw_cmd, 3739),
    Function.raw_ability(394, "Morph_OrbitalCommand_quick", raw_cmd, 1516),
    Function.raw_ability(395, "Morph_OverlordTransport_quick", raw_cmd, 2708),
    Function.raw_ability(397, "Morph_OverseerMode_quick", raw_cmd, 3745),
    Function.raw_ability(396, "Morph_Overseer_quick", raw_cmd, 1448),
    Function.raw_ability(398, "Morph_OversightMode_quick", raw_cmd, 3743),
    Function.raw_ability(399, "Morph_PlanetaryFortress_quick", raw_cmd, 1450),
    Function.raw_ability(400, "Morph_Ravager_quick", raw_cmd, 2330),
    Function.raw_ability(401, "Morph_Root_pt", raw_cmd_pt, 3680),
    Function.raw_ability(402, "Morph_SiegeMode_quick", raw_cmd, 388),
    Function.raw_ability(403, "Morph_SpineCrawlerRoot_pt", raw_cmd_pt, 1729, 3680),
    Function.raw_ability(404, "Morph_SpineCrawlerUproot_quick", raw_cmd, 1725, 3681),
    Function.raw_ability(405, "Morph_SporeCrawlerRoot_pt", raw_cmd_pt, 1731, 3680),
    Function.raw_ability(406, "Morph_SporeCrawlerUproot_quick", raw_cmd, 1727, 3681),
    Function.raw_ability(407, "Morph_SupplyDepot_Lower_quick", raw_cmd, 556),
    Function.raw_ability(408, "Morph_SupplyDepot_Raise_quick", raw_cmd, 558),
    Function.raw_ability(160, "Morph_SurveillanceMode_quick", raw_cmd, 3741),
    Function.raw_ability(409, "Morph_ThorExplosiveMode_quick", raw_cmd, 2364),
    Function.raw_ability(410, "Morph_ThorHighImpactMode_quick", raw_cmd, 2362),
    Function.raw_ability(411, "Morph_Unsiege_quick", raw_cmd, 390),
    Function.raw_ability(412, "Morph_Uproot_quick", raw_cmd, 3681),
    Function.raw_ability(413, "Morph_VikingAssaultMode_quick", raw_cmd, 403),
    Function.raw_ability(414, "Morph_VikingFighterMode_quick", raw_cmd, 405),
    Function.raw_ability(77, "Morph_WarpGate_quick", raw_cmd, 1518),
    Function.raw_ability(544, "Morph_WarpGate_autocast", raw_autocast, 1518),
    Function.raw_ability(80, "Morph_WarpPrismPhasingMode_quick", raw_cmd, 1528),
    Function.raw_ability(81, "Morph_WarpPrismTransportMode_quick", raw_cmd, 1530),
    Function.raw_ability(13, "Move_pt", raw_cmd_pt, 3794),
    Function.raw_ability(14, "Move_unit", raw_cmd_unit, 3794),
    Function.raw_ability(545, "Move_Battlecruiser_pt", raw_cmd_pt, 3776, 3794),
    Function.raw_ability(546, "Move_Battlecruiser_unit", raw_cmd_unit, 3776, 3794),
    Function.raw_ability(547, "Move_Move_pt", raw_cmd_pt, 16, 3794),
    Function.raw_ability(548, "Move_Move_unit", raw_cmd_unit, 16, 3794),
    Function.raw_ability(15, "Patrol_pt", raw_cmd_pt, 3795),
    Function.raw_ability(16, "Patrol_unit", raw_cmd_unit, 3795),
    Function.raw_ability(549, "Patrol_Battlecruiser_pt", raw_cmd_pt, 3777, 3795),
    Function.raw_ability(550, "Patrol_Battlecruiser_unit", raw_cmd_unit, 3777, 3795),
    Function.raw_ability(551, "Patrol_Patrol_pt", raw_cmd_pt, 17, 3795),
    Function.raw_ability(552, "Patrol_Patrol_unit", raw_cmd_unit, 17, 3795),
    Function.raw_ability(415, "Rally_Building_pt", raw_cmd_pt, 195, 3673),
    Function.raw_ability(416, "Rally_Building_unit", raw_cmd_unit, 195, 3673),
    Function.raw_ability(417, "Rally_CommandCenter_pt", raw_cmd_pt, 203, 3690),
    Function.raw_ability(418, "Rally_CommandCenter_unit", raw_cmd_unit, 203, 3690),
    Function.raw_ability(419, "Rally_Hatchery_Units_pt", raw_cmd_pt, 211, 3673),
    Function.raw_ability(420, "Rally_Hatchery_Units_unit", raw_cmd_unit, 211, 3673),
    Function.raw_ability(421, "Rally_Hatchery_Workers_pt", raw_cmd_pt, 212, 3690),
    Function.raw_ability(422, "Rally_Hatchery_Workers_unit", raw_cmd_unit, 212, 3690),
    Function.raw_ability(423, "Rally_Morphing_Unit_pt", raw_cmd_pt, 199, 3673),
    Function.raw_ability(424, "Rally_Morphing_Unit_unit", raw_cmd_unit, 199, 3673),
    Function.raw_ability(138, "Rally_Nexus_pt", raw_cmd_pt, 207, 3690),
    Function.raw_ability(165, "Rally_Nexus_unit", raw_cmd_unit, 207, 3690),
    Function.raw_ability(106, "Rally_Units_pt", raw_cmd_pt, 3673),
    Function.raw_ability(107, "Rally_Units_unit", raw_cmd_unit, 3673),
    Function.raw_ability(114, "Rally_Workers_pt", raw_cmd_pt, 3690),
    Function.raw_ability(115, "Rally_Workers_unit", raw_cmd_unit, 3690),
    Function.raw_ability(425, "Research_AdaptiveTalons_quick", raw_cmd, 3709),
    Function.raw_ability(85, "Research_AdeptResonatingGlaives_quick", raw_cmd, 1594),
    Function.raw_ability(426, "Research_AdvancedBallistics_quick", raw_cmd, 805),
    Function.raw_ability(553, "Research_AnabolicSynthesis_quick", raw_cmd, 263),
    Function.raw_ability(427, "Research_BansheeCloakingField_quick", raw_cmd, 790),
    Function.raw_ability(428, "Research_BansheeHyperflightRotors_quick", raw_cmd, 799),
    Function.raw_ability(429, "Research_BattlecruiserWeaponRefit_quick", raw_cmd, 1532),
    Function.raw_ability(84, "Research_Blink_quick", raw_cmd, 1593),
    Function.raw_ability(430, "Research_Burrow_quick", raw_cmd, 1225),
    Function.raw_ability(431, "Research_CentrifugalHooks_quick", raw_cmd, 1482),
    Function.raw_ability(83, "Research_Charge_quick", raw_cmd, 1592),
    Function.raw_ability(432, "Research_ChitinousPlating_quick", raw_cmd, 265),
    Function.raw_ability(433, "Research_CombatShield_quick", raw_cmd, 731),
    Function.raw_ability(434, "Research_ConcussiveShells_quick", raw_cmd, 732),
    Function.raw_ability(554, "Research_CycloneLockOnDamage_quick", raw_cmd, 769),
    Function.raw_ability(435, "Research_CycloneRapidFireLaunchers_quick", raw_cmd, 768),
    Function.raw_ability(436, "Research_DrillingClaws_quick", raw_cmd, 764),
    Function.raw_ability(563, "Research_EnhancedShockwaves_quick", raw_cmd, 822),
    Function.raw_ability(69, "Research_ExtendedThermalLance_quick", raw_cmd, 1097),
    Function.raw_ability(437, "Research_GlialRegeneration_quick", raw_cmd, 216),
    Function.raw_ability(67, "Research_GraviticBooster_quick", raw_cmd, 1093),
    Function.raw_ability(68, "Research_GraviticDrive_quick", raw_cmd, 1094),
    Function.raw_ability(438, "Research_GroovedSpines_quick", raw_cmd, 1282),
    Function.raw_ability(440, "Research_HighCapacityFuelTanks_quick", raw_cmd, 804),
    Function.raw_ability(439, "Research_HiSecAutoTracking_quick", raw_cmd, 650),
    Function.raw_ability(441, "Research_InfernalPreigniter_quick", raw_cmd, 761),
    Function.raw_ability(18, "Research_InterceptorGravitonCatapult_quick", raw_cmd, 44),
    Function.raw_ability(442, "Research_MuscularAugments_quick", raw_cmd, 1283),
    Function.raw_ability(443, "Research_NeosteelFrame_quick", raw_cmd, 655),
    Function.raw_ability(444, "Research_NeuralParasite_quick", raw_cmd, 1455),
    Function.raw_ability(445, "Research_PathogenGlands_quick", raw_cmd, 1454),
    Function.raw_ability(446, "Research_PersonalCloaking_quick", raw_cmd, 820),
    Function.raw_ability(19, "Research_PhoenixAnionPulseCrystals_quick", raw_cmd, 46),
    Function.raw_ability(447, "Research_PneumatizedCarapace_quick", raw_cmd, 1223),
    Function.raw_ability(139, "Research_ProtossAirArmorLevel1_quick", raw_cmd, 1565, 3692),
    Function.raw_ability(140, "Research_ProtossAirArmorLevel2_quick", raw_cmd, 1566, 3692),
    Function.raw_ability(141, "Research_ProtossAirArmorLevel3_quick", raw_cmd, 1567, 3692),
    Function.raw_ability(116, "Research_ProtossAirArmor_quick", raw_cmd, 3692),
    Function.raw_ability(142, "Research_ProtossAirWeaponsLevel1_quick", raw_cmd, 1562, 3693),
    Function.raw_ability(143, "Research_ProtossAirWeaponsLevel2_quick", raw_cmd, 1563, 3693),
    Function.raw_ability(144, "Research_ProtossAirWeaponsLevel3_quick", raw_cmd, 1564, 3693),
    Function.raw_ability(117, "Research_ProtossAirWeapons_quick", raw_cmd, 3693),
    Function.raw_ability(145, "Research_ProtossGroundArmorLevel1_quick", raw_cmd, 1065, 3694),
    Function.raw_ability(146, "Research_ProtossGroundArmorLevel2_quick", raw_cmd, 1066, 3694),
    Function.raw_ability(147, "Research_ProtossGroundArmorLevel3_quick", raw_cmd, 1067, 3694),
    Function.raw_ability(118, "Research_ProtossGroundArmor_quick", raw_cmd, 3694),
    Function.raw_ability(148, "Research_ProtossGroundWeaponsLevel1_quick", raw_cmd, 1062, 3695),
    Function.raw_ability(149, "Research_ProtossGroundWeaponsLevel2_quick", raw_cmd, 1063, 3695),
    Function.raw_ability(150, "Research_ProtossGroundWeaponsLevel3_quick", raw_cmd, 1064, 3695),
    Function.raw_ability(119, "Research_ProtossGroundWeapons_quick", raw_cmd, 3695),
    Function.raw_ability(151, "Research_ProtossShieldsLevel1_quick", raw_cmd, 1068, 3696),
    Function.raw_ability(152, "Research_ProtossShieldsLevel2_quick", raw_cmd, 1069, 3696),
    Function.raw_ability(153, "Research_ProtossShieldsLevel3_quick", raw_cmd, 1070, 3696),
    Function.raw_ability(120, "Research_ProtossShields_quick", raw_cmd, 3696),
    Function.raw_ability(70, "Research_PsiStorm_quick", raw_cmd, 1126),
    Function.raw_ability(448, "Research_RavenCorvidReactor_quick", raw_cmd, 793),
    Function.raw_ability(449, "Research_RavenRecalibratedExplosives_quick", raw_cmd, 803),
    Function.raw_ability(97, "Research_ShadowStrike_quick", raw_cmd, 2720),
    Function.raw_ability(450, "Research_SmartServos_quick", raw_cmd, 766),
    Function.raw_ability(451, "Research_Stimpack_quick", raw_cmd, 730),
    Function.raw_ability(453, "Research_TerranInfantryArmorLevel1_quick", raw_cmd, 656, 3697),
    Function.raw_ability(454, "Research_TerranInfantryArmorLevel2_quick", raw_cmd, 657, 3697),
    Function.raw_ability(455, "Research_TerranInfantryArmorLevel3_quick", raw_cmd, 658, 3697),
    Function.raw_ability(452, "Research_TerranInfantryArmor_quick", raw_cmd, 3697),
    Function.raw_ability(457, "Research_TerranInfantryWeaponsLevel1_quick", raw_cmd, 652, 3698),
    Function.raw_ability(458, "Research_TerranInfantryWeaponsLevel2_quick", raw_cmd, 653, 3698),
    Function.raw_ability(459, "Research_TerranInfantryWeaponsLevel3_quick", raw_cmd, 654, 3698),
    Function.raw_ability(456, "Research_TerranInfantryWeapons_quick", raw_cmd, 3698),
    Function.raw_ability(461, "Research_TerranShipWeaponsLevel1_quick", raw_cmd, 861, 3699),
    Function.raw_ability(462, "Research_TerranShipWeaponsLevel2_quick", raw_cmd, 862, 3699),
    Function.raw_ability(463, "Research_TerranShipWeaponsLevel3_quick", raw_cmd, 863, 3699),
    Function.raw_ability(460, "Research_TerranShipWeapons_quick", raw_cmd, 3699),
    Function.raw_ability(464, "Research_TerranStructureArmorUpgrade_quick", raw_cmd, 651),
    Function.raw_ability(466, "Research_TerranVehicleAndShipPlatingLevel1_quick", raw_cmd, 864, 3700),
    Function.raw_ability(467, "Research_TerranVehicleAndShipPlatingLevel2_quick", raw_cmd, 865, 3700),
    Function.raw_ability(468, "Research_TerranVehicleAndShipPlatingLevel3_quick", raw_cmd, 866, 3700),
    Function.raw_ability(465, "Research_TerranVehicleAndShipPlating_quick", raw_cmd, 3700),
    Function.raw_ability(470, "Research_TerranVehicleWeaponsLevel1_quick", raw_cmd, 855, 3701),
    Function.raw_ability(471, "Research_TerranVehicleWeaponsLevel2_quick", raw_cmd, 856, 3701),
    Function.raw_ability(472, "Research_TerranVehicleWeaponsLevel3_quick", raw_cmd, 857, 3701),
    Function.raw_ability(469, "Research_TerranVehicleWeapons_quick", raw_cmd, 3701),
    Function.raw_ability(473, "Research_TunnelingClaws_quick", raw_cmd, 217),
    Function.raw_ability(82, "Research_WarpGate_quick", raw_cmd, 1568),
    Function.raw_ability(475, "Research_ZergFlyerArmorLevel1_quick", raw_cmd, 1315, 3702),
    Function.raw_ability(476, "Research_ZergFlyerArmorLevel2_quick", raw_cmd, 1316, 3702),
    Function.raw_ability(477, "Research_ZergFlyerArmorLevel3_quick", raw_cmd, 1317, 3702),
    Function.raw_ability(474, "Research_ZergFlyerArmor_quick", raw_cmd, 3702),
    Function.raw_ability(479, "Research_ZergFlyerAttackLevel1_quick", raw_cmd, 1312, 3703),
    Function.raw_ability(480, "Research_ZergFlyerAttackLevel2_quick", raw_cmd, 1313, 3703),
    Function.raw_ability(481, "Research_ZergFlyerAttackLevel3_quick", raw_cmd, 1314, 3703),
    Function.raw_ability(478, "Research_ZergFlyerAttack_quick", raw_cmd, 3703),
    Function.raw_ability(483, "Research_ZergGroundArmorLevel1_quick", raw_cmd, 1189, 3704),
    Function.raw_ability(484, "Research_ZergGroundArmorLevel2_quick", raw_cmd, 1190, 3704),
    Function.raw_ability(485, "Research_ZergGroundArmorLevel3_quick", raw_cmd, 1191, 3704),
    Function.raw_ability(482, "Research_ZergGroundArmor_quick", raw_cmd, 3704),
    Function.raw_ability(494, "Research_ZerglingAdrenalGlands_quick", raw_cmd, 1252),
    Function.raw_ability(495, "Research_ZerglingMetabolicBoost_quick", raw_cmd, 1253),
    Function.raw_ability(487, "Research_ZergMeleeWeaponsLevel1_quick", raw_cmd, 1186, 3705),
    Function.raw_ability(488, "Research_ZergMeleeWeaponsLevel2_quick", raw_cmd, 1187, 3705),
    Function.raw_ability(489, "Research_ZergMeleeWeaponsLevel3_quick", raw_cmd, 1188, 3705),
    Function.raw_ability(486, "Research_ZergMeleeWeapons_quick", raw_cmd, 3705),
    Function.raw_ability(491, "Research_ZergMissileWeaponsLevel1_quick", raw_cmd, 1192, 3706),
    Function.raw_ability(492, "Research_ZergMissileWeaponsLevel2_quick", raw_cmd, 1193, 3706),
    Function.raw_ability(493, "Research_ZergMissileWeaponsLevel3_quick", raw_cmd, 1194, 3706),
    Function.raw_ability(490, "Research_ZergMissileWeapons_quick", raw_cmd, 3706),
    Function.raw_ability(10, "Scan_Move_pt", raw_cmd_pt, 19, 3674),
    Function.raw_ability(11, "Scan_Move_unit", raw_cmd_unit, 19, 3674),
    Function.raw_ability(1, "Smart_pt", raw_cmd_pt, 1),
    Function.raw_ability(12, "Smart_unit", raw_cmd_unit, 1),
    Function.raw_ability(101, "Stop_quick", raw_cmd, 3665),
    Function.raw_ability(555, "Stop_Battlecruiser_quick", raw_cmd, 3783, 3665),
    Function.raw_ability(496, "Stop_Building_quick", raw_cmd, 2057, 3665),
    Function.raw_ability(497, "Stop_Redirect_quick", raw_cmd, 1691, 3665),
    Function.raw_ability(155, "Stop_Stop_quick", raw_cmd, 4, 3665),
    Function.raw_ability(54, "Train_Adept_quick", raw_cmd, 922),
    Function.raw_ability(498, "Train_Baneling_quick", raw_cmd, 80),
    Function.raw_ability(499, "Train_Banshee_quick", raw_cmd, 621),
    Function.raw_ability(500, "Train_Battlecruiser_quick", raw_cmd, 623),
    Function.raw_ability(56, "Train_Carrier_quick", raw_cmd, 948),
    Function.raw_ability(62, "Train_Colossus_quick", raw_cmd, 978),
    Function.raw_ability(501, "Train_Corruptor_quick", raw_cmd, 1353),
    Function.raw_ability(502, "Train_Cyclone_quick", raw_cmd, 597),
    Function.raw_ability(52, "Train_DarkTemplar_quick", raw_cmd, 920),
    Function.raw_ability(166, "Train_Disruptor_quick", raw_cmd, 994),
    Function.raw_ability(503, "Train_Drone_quick", raw_cmd, 1342),
    Function.raw_ability(504, "Train_Ghost_quick", raw_cmd, 562),
    Function.raw_ability(505, "Train_Hellbat_quick", raw_cmd, 596),
    Function.raw_ability(506, "Train_Hellion_quick", raw_cmd, 595),
    Function.raw_ability(51, "Train_HighTemplar_quick", raw_cmd, 919),
    Function.raw_ability(507, "Train_Hydralisk_quick", raw_cmd, 1345),
    Function.raw_ability(63, "Train_Immortal_quick", raw_cmd, 979),
    Function.raw_ability(508, "Train_Infestor_quick", raw_cmd, 1352),
    Function.raw_ability(509, "Train_Liberator_quick", raw_cmd, 626),
    Function.raw_ability(510, "Train_Marauder_quick", raw_cmd, 563),
    Function.raw_ability(511, "Train_Marine_quick", raw_cmd, 560),
    Function.raw_ability(512, "Train_Medivac_quick", raw_cmd, 620),
    Function.raw_ability(513, "Train_MothershipCore_quick", raw_cmd, 1853),
    Function.raw_ability(21, "Train_Mothership_quick", raw_cmd, 110),
    Function.raw_ability(514, "Train_Mutalisk_quick", raw_cmd, 1346),
    Function.raw_ability(61, "Train_Observer_quick", raw_cmd, 977),
    Function.raw_ability(58, "Train_Oracle_quick", raw_cmd, 954),
    Function.raw_ability(515, "Train_Overlord_quick", raw_cmd, 1344),
    Function.raw_ability(55, "Train_Phoenix_quick", raw_cmd, 946),
    Function.raw_ability(64, "Train_Probe_quick", raw_cmd, 1006),
    Function.raw_ability(516, "Train_Queen_quick", raw_cmd, 1632),
    Function.raw_ability(517, "Train_Raven_quick", raw_cmd, 622),
    Function.raw_ability(518, "Train_Reaper_quick", raw_cmd, 561),
    Function.raw_ability(519, "Train_Roach_quick", raw_cmd, 1351),
    Function.raw_ability(520, "Train_SCV_quick", raw_cmd, 524),
    Function.raw_ability(53, "Train_Sentry_quick", raw_cmd, 921),
    Function.raw_ability(521, "Train_SiegeTank_quick", raw_cmd, 591),
    Function.raw_ability(50, "Train_Stalker_quick", raw_cmd, 917),
    Function.raw_ability(522, "Train_SwarmHost_quick", raw_cmd, 1356),
    Function.raw_ability(59, "Train_Tempest_quick", raw_cmd, 955),
    Function.raw_ability(523, "Train_Thor_quick", raw_cmd, 594),
    Function.raw_ability(524, "Train_Ultralisk_quick", raw_cmd, 1348),
    Function.raw_ability(525, "Train_VikingFighter_quick", raw_cmd, 624),
    Function.raw_ability(526, "Train_Viper_quick", raw_cmd, 1354),
    Function.raw_ability(57, "Train_VoidRay_quick", raw_cmd, 950),
    Function.raw_ability(76, "TrainWarp_Adept_pt", raw_cmd_pt, 1419),
    Function.raw_ability(74, "TrainWarp_DarkTemplar_pt", raw_cmd_pt, 1417),
    Function.raw_ability(73, "TrainWarp_HighTemplar_pt", raw_cmd_pt, 1416),
    Function.raw_ability(60, "Train_WarpPrism_quick", raw_cmd, 976),
    Function.raw_ability(75, "TrainWarp_Sentry_pt", raw_cmd_pt, 1418),
    Function.raw_ability(72, "TrainWarp_Stalker_pt", raw_cmd_pt, 1414),
    Function.raw_ability(71, "TrainWarp_Zealot_pt", raw_cmd_pt, 1413),
    Function.raw_ability(527, "Train_WidowMine_quick", raw_cmd, 614),
    Function.raw_ability(49, "Train_Zealot_quick", raw_cmd, 916),
    Function.raw_ability(528, "Train_Zergling_quick", raw_cmd, 1343),
    Function.raw_ability(529, "UnloadAllAt_Medivac_pt", raw_cmd_pt, 396, 3669),
    Function.raw_ability(530, "UnloadAllAt_Medivac_unit", raw_cmd_unit, 396, 3669),
    Function.raw_ability(531, "UnloadAllAt_Overlord_pt", raw_cmd_pt, 1408, 3669),
    Function.raw_ability(532, "UnloadAllAt_Overlord_unit", raw_cmd_unit, 1408, 3669),
    Function.raw_ability(105, "UnloadAllAt_pt", raw_cmd_pt, 3669),
    Function.raw_ability(164, "UnloadAllAt_unit", raw_cmd_unit, 3669),
    Function.raw_ability(156, "UnloadAllAt_WarpPrism_pt", raw_cmd_pt, 913, 3669),
    Function.raw_ability(163, "UnloadAllAt_WarpPrism_unit", raw_cmd_unit, 913, 3669),
    Function.raw_ability(533, "UnloadAll_Bunker_quick", raw_cmd, 408, 3664),
    Function.raw_ability(534, "UnloadAll_CommandCenter_quick", raw_cmd, 413, 3664),
    Function.raw_ability(535, "UnloadAll_NydusNetwork_quick", raw_cmd, 1438, 3664),
    Function.raw_ability(536, "UnloadAll_NydusWorm_quick", raw_cmd, 2371, 3664),
    Function.raw_ability(100, "UnloadAll_quick", raw_cmd, 3664),
    Function.raw_ability(556, "UnloadUnit_quick", raw_cmd, 3796),
    Function.raw_ability(557, "UnloadUnit_Bunker_quick", raw_cmd, 410, 3796),
    Function.raw_ability(558, "UnloadUnit_CommandCenter_quick", raw_cmd, 415, 3796),
    Function.raw_ability(559, "UnloadUnit_Medivac_quick", raw_cmd, 397, 3796),
    Function.raw_ability(560, "UnloadUnit_NydusNetwork_quick", raw_cmd, 1440, 3796),
    Function.raw_ability(561, "UnloadUnit_Overlord_quick", raw_cmd, 1409, 3796),
    Function.raw_ability(562, "UnloadUnit_WarpPrism_quick", raw_cmd, 914, 3796),
]
# pylint: enable=line-too-long

# Create an IntEnum of the function names/ids so that printing the id will
# show something useful.
_Raw_Functions = enum.IntEnum(  # pylint: disable=invalid-name
    "_Raw_Functions", {f.name: f.id for f in _RAW_FUNCTIONS})
_RAW_FUNCTIONS = [f._replace(id=_Raw_Functions(f.id)) for f in _RAW_FUNCTIONS]
RAW_FUNCTIONS = Functions(_RAW_FUNCTIONS)

# Some indexes to support features.py and action conversion.
RAW_ABILITY_IDS = collections.defaultdict(set)  # {ability_id: {funcs}}
for _func in RAW_FUNCTIONS:
  if _func.ability_id >= 0:
    RAW_ABILITY_IDS[_func.ability_id].add(_func)
RAW_ABILITY_IDS = {k: frozenset(v) for k, v in RAW_ABILITY_IDS.items()}
RAW_FUNCTIONS_AVAILABLE = {f.id: f for f in RAW_FUNCTIONS if f.avail_fn}
RAW_ABILITY_ID_TO_FUNC_ID = {k: min(f.id for f in v)  # pylint: disable=g-complex-comprehension
                             for k, v in RAW_ABILITY_IDS.items()}


class FunctionCall(collections.namedtuple(
    "FunctionCall", ["function", "arguments"])):
  """Represents a function call action.

  Attributes:
    function: Store the function id, eg 2 for select_point.
    arguments: The list of arguments for that function, each being a list of
        ints. For select_point this could be: [[0], [23, 38]].
  """
  __slots__ = ()

  @classmethod
  def init_with_validation(cls, function, arguments, raw=False):
    """Return a `FunctionCall` given some validation for the function and args.

    Args:
      function: A function name or id, to be converted into a function id enum.
      arguments: An iterable of function arguments. Arguments that are enum
          types can be passed by name. Arguments that only take one value (ie
          not a point) don't need to be wrapped in a list.
      raw: Whether this is a raw function call.

    Returns:
      A new `FunctionCall` instance.

    Raises:
      KeyError: if the enum name doesn't exist.
      ValueError: if the enum id doesn't exist.
    """
    func = RAW_FUNCTIONS[function] if raw else FUNCTIONS[function]
    args = []
    for arg, arg_type in zip(arguments, func.args):
      arg = numpy_to_python(arg)
      if arg_type.values:  # Allow enum values by name or int.
        if isinstance(arg, str):
          try:
            args.append([arg_type.values[arg]])
          except KeyError:
            raise KeyError("Unknown argument value: %s, valid values: %s" % (
                arg, [v.name for v in arg_type.values]))
        else:
          if isinstance(arg, list):
            arg = arg[0]
          try:
            args.append([arg_type.values(arg)])
          except ValueError:
            raise ValueError("Unknown argument value: %s, valid values: %s" % (
                arg, list(arg_type.values)))
      elif isinstance(arg, int):  # Allow bare ints.
        args.append([arg])
      elif isinstance(arg, list):
        args.append(arg)
      else:
        raise ValueError(
            "Unknown argument value type: %s, expected int or list of ints, or "
            "their numpy equivalents. Value: %s" % (type(arg), arg))
    return cls(func.id, args)

  @classmethod
  def all_arguments(cls, function, arguments, raw=False):
    """Helper function for creating `FunctionCall`s with `Arguments`.

    Args:
      function: The value to store for the action function.
      arguments: The values to store for the arguments of the action. Can either
        be an `Arguments` object, a `dict`, or an iterable. If a `dict` or an
        iterable is provided, the values will be unpacked into an `Arguments`
        object.
      raw: Whether this is a raw function call.

    Returns:
      A new `FunctionCall` instance.
    """
    args_type = RawArguments if raw else Arguments

    if isinstance(arguments, dict):
      arguments = args_type(**arguments)
    elif not isinstance(arguments, args_type):
      arguments = args_type(*arguments)
    return cls(function, arguments)

  def __reduce__(self):
    return self.__class__, tuple(self)


class ValidActions(collections.namedtuple(
    "ValidActions", ["types", "functions"])):
  """The set of types and functions that are valid for an agent to use.

  Attributes:
    types: A namedtuple of the types that the functions require. Unlike TYPES
        above, this includes the sizes for screen and minimap.
    functions: A namedtuple of all the functions.
  """
  __slots__ = ()

  def __reduce__(self):
    return self.__class__, tuple(self)
