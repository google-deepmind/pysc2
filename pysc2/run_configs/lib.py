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
"""Configs for various ways to run starcraft."""

import collections
import datetime
import os

from pysc2.lib import gfile


class Version(collections.namedtuple("Version", [
    "game_version", "build_version", "data_version", "binary"])):
  """Represents a single version of the game."""
  __slots__ = ()


def version_dict(versions):
  return {ver.game_version: ver for ver in versions}


# https://github.com/Blizzard/s2client-proto/blob/master/buildinfo/versions.json
# Generate with bin/gen_versions.py or bin/replay_version.py.
VERSIONS = version_dict([
    Version("3.13.0", 52910, "8D9FEF2E1CF7C6C9CBE4FBCA830DDE1C", None),
    Version("3.14.0", 53644, "CA275C4D6E213ED30F80BACCDFEDB1F5", None),
    Version("3.15.0", 54518, "BBF619CCDCC80905350F34C2AF0AB4F6", None),
    Version("3.15.1", 54518, "6EB25E687F8637457538F4B005950A5E", None),
    Version("3.16.0", 55505, "60718A7CA50D0DF42987A30CF87BCB80", None),
    Version("3.16.1", 55958, "5BD7C31B44525DAB46E64C4602A81DC2", None),
    Version("3.17.0", 56787, "DFD1F6607F2CF19CB4E1C996B2563D9B", None),
    Version("3.17.1", 56787, "3F2FCED08798D83B873B5543BEFA6C4B", None),
    Version("3.17.2", 56787, "C690FC543082D35EA0AAA876B8362BEA", None),
    Version("3.18.0", 57507, "1659EF34997DA3470FF84A14431E3A86", None),
    Version("3.19.0", 58400, "2B06AEE58017A7DF2A3D452D733F1019", None),
    Version("3.19.1", 58400, "D9B568472880CC4719D1B698C0D86984", None),
    Version("4.0.0", 59587, "9B4FD995C61664831192B7DA46F8C1A1", None),
    Version("4.0.2", 59587, "B43D9EE00A363DAFAD46914E3E4AF362", None),
    Version("4.1.0", 60196, "1B8ACAB0C663D5510941A9871B3E9FBE", None),
    Version("4.1.1", 60321, "5C021D8A549F4A776EE9E9C1748FFBBC", None),
    Version("4.1.2", 60321, "33D9FE28909573253B7FC352CE7AEA40", None),
    Version("4.1.3", 60321, "F486693E00B2CD305B39E0AB254623EB", None),
    Version("4.1.4", 60321, "2E2A3F6E0BAFE5AC659C4D39F13A938C", None),
    Version("4.2.0", 62347, "C0C0E9D37FCDBC437CE386C6BE2D1F93", None),
    Version("4.2.1", 62848, "29BBAC5AFF364B6101B661DB468E3A37", None),
    Version("4.2.2", 63454, "3CB54C86777E78557C984AB1CF3494A0", None),
    Version("4.2.3", 63454, "5E3A8B21E41B987E05EE4917AAD68C69", None),
    Version("4.2.4", 63454, "7C51BC7B0841EACD3535E6FA6FF2116B", None),
    Version("4.3.0", 64469, "C92B3E9683D5A59E08FC011F4BE167FF", None),
    Version("4.3.1", 65094, "E5A21037AA7A25C03AC441515F4E0644", None),
    Version("4.3.2", 65384, "B6D73C85DFB70F5D01DEABB2517BF11C", None),
    Version("4.4.0", 65895, "BF41339C22AE2EDEBEEADC8C75028F7D", None),
    Version("4.4.1", 66668, "C094081D274A39219061182DBFD7840F", None),
    Version("4.5.0", 67188, "2ACF84A7ECBB536F51FC3F734EC3019F", None),
    Version("4.5.1", 67188, "6D239173B8712461E6A7C644A5539369", None),
    Version("4.6.0", 67926, "7DE59231CBF06F1ECE9A25A27964D4AE", None),
    Version("4.6.1", 67926, "BEA99B4A8E7B41E62ADC06D194801BAB", None),
    Version("4.6.2", 69232, "B3E14058F1083913B80C20993AC965DB", None),
    Version("4.7.0", 70154, "8E216E34BC61ABDE16A59A672ACB0F3B", None),
    Version("4.7.1", 70154, "94596A85191583AD2EBFAE28C5D532DB", None),
    Version("4.8.0", 71061, "760581629FC458A1937A05ED8388725B", None),
    Version("4.8.1", 71523, "FCAF3F050B7C0CC7ADCF551B61B9B91E", None),
    Version("4.8.2", 71663, "FE90C92716FC6F8F04B74268EC369FA5", None),
    Version("4.8.3", 72282, "0F14399BBD0BA528355FF4A8211F845B", None),
    Version("4.8.4", 73286, "CD040C0675FD986ED37A4CA3C88C8EB5", None),
    Version("4.8.5", 73559, "B2465E73AED597C74D0844112D582595", None),
    Version("4.8.6", 73620, "AA18FEAD6573C79EF707DF44ABF1BE61", None),
    Version("4.9.0", 74071, "70C74A2DCA8A0D8E7AE8647CAC68ACCA", None),
    Version("4.9.1", 74456, "218CB2271D4E2FA083470D30B1A05F02", None),
    Version("4.9.2", 74741, "614480EF79264B5BD084E57F912172FF", None),
    Version("4.9.3", 75025, "C305368C63621480462F8F516FB64374", None),
    Version("4.10.0", 75689, "B89B5D6FA7CBF6452E721311BFBC6CB2", None),
    Version("4.10.1", 75800, "DDFFF9EC4A171459A4F371C6CC189554", None),
    Version("4.10.2", 76052, "D0F1A68AA88BA90369A84CD1439AA1C3", None),
    Version("4.10.3", 76114, "CDB276D311F707C29BA664B7754A7293", None),
    Version("4.10.4", 76811, "FF9FA4EACEC5F06DEB27BD297D73ED67", None),
    Version("4.11.0", 77379, "70E774E722A58287EF37D487605CD384", None),
    Version("4.11.1", 77379, "F92D1127A291722120AC816F09B2E583", None),
    Version("4.11.2", 77535, "FC43E0897FCC93E4632AC57CBC5A2137", None),
    Version("4.11.3", 77661, "A15B8E4247434B020086354F39856C51", None),
    Version("4.11.4", 78285, "69493AFAB5C7B45DDB2F3442FD60F0CF", None),
    Version("4.12.0", 79998, "B47567DEE5DC23373BFF57194538DFD3", None),
    Version("4.12.1", 80188, "44DED5AED024D23177C742FC227C615A", None),
    Version("5.0.0", 80949, "9AE39C332883B8BF6AA190286183ED72", None),
    Version("5.0.1", 81009, "0D28678BC32E7F67A238F19CD3E0A2CE", None),
    Version("5.0.2", 81102, "DC0A1182FB4ABBE8E29E3EC13CF46F68", None),
    Version("5.0.3", 81433, "5FD8D4B6B52723B44862DF29F232CF31", None),
    Version("5.0.4", 82457, "D2707E265785612D12B381AF6ED9DBF4", None),
    Version("5.0.5", 82893, "D795328C01B8A711947CC62AA9750445", None),
    Version("5.0.6", 83830, "B4745D6A4F982A3143C183D8ACB6C3E3", None),
    Version("5.0.7", 84643, "A389D1F7DF9DD792FBE980533B7119FF", None),
    Version("5.0.8", 86383, "22EAC562CD0C6A31FB2C2C21E3AA3680", None),
    Version("5.0.9", 87702, "F799E093428D419FD634CCE9B925218C", None),
])


class RunConfig(object):
  """Base class for different run configs."""

  def __init__(self, replay_dir, data_dir, tmp_dir, version,
               cwd=None, env=None):
    """Initialize the runconfig with the various directories needed.

    Args:
      replay_dir: Where to find replays. Might not be accessible to SC2.
      data_dir: Where SC2 should find the data and battle.net cache.
      tmp_dir: The temporary directory. None is system default.
      version: The game version to run, a string.
      cwd: Where to set the current working directory.
      env: What to pass as the environment variables.
    """
    self.replay_dir = replay_dir
    self.data_dir = data_dir
    self.tmp_dir = tmp_dir
    self.cwd = cwd
    self.env = env
    self.version = self._get_version(version)

  def map_data(self, map_name, players=None):
    """Return the map data for a map by name or path."""
    map_names = [map_name]
    if players:
      map_names.append(os.path.join(
          os.path.dirname(map_name),
          "(%s)%s" % (players, os.path.basename(map_name))))
    for name in map_names:
      path = os.path.join(self.data_dir, "Maps", name)
      if gfile.Exists(path):
        with gfile.Open(path, "rb") as f:
          return f.read()
    raise ValueError(f"Map {map_name} not found in {self.data_dir}/Maps.")

  def abs_replay_path(self, replay_path):
    """Return the absolute path to the replay, outside the sandbox."""
    return os.path.join(self.replay_dir, replay_path)

  def replay_data(self, replay_path):
    """Return the replay data given a path to the replay."""
    with gfile.Open(self.abs_replay_path(replay_path), "rb") as f:
      return f.read()

  def replay_paths(self, replay_dir):
    """A generator yielding the full path to the replays under `replay_dir`."""
    replay_dir = self.abs_replay_path(replay_dir)
    if replay_dir.lower().endswith(".sc2replay"):
      yield replay_dir
      return
    for f in gfile.ListDir(replay_dir):
      if f.lower().endswith(".sc2replay"):
        yield os.path.join(replay_dir, f)

  def save_replay(self, replay_data, replay_dir, prefix=None):
    """Save a replay to a directory, returning the path to the replay.

    Args:
      replay_data: The result of controller.save_replay(), ie the binary data.
      replay_dir: Where to save the replay. This can be absolute or relative.
      prefix: Optional prefix for the replay filename.

    Returns:
      The full path where the replay is saved.

    Raises:
      ValueError: If the prefix contains the path seperator.
    """
    if not prefix:
      replay_filename = ""
    elif os.path.sep in prefix:
      raise ValueError("Prefix '%s' contains '%s', use replay_dir instead." % (
          prefix, os.path.sep))
    else:
      replay_filename = prefix + "_"
    now = datetime.datetime.utcnow().replace(microsecond=0)
    replay_filename += "%s.SC2Replay" % now.isoformat("-").replace(":", "-")
    replay_dir = self.abs_replay_path(replay_dir)
    if not gfile.Exists(replay_dir):
      gfile.MakeDirs(replay_dir)
    replay_path = os.path.join(replay_dir, replay_filename)
    with gfile.Open(replay_path, "wb") as f:
      f.write(replay_data)
    return replay_path

  def start(self, version=None, **kwargs):
    """Launch the game. Find the version and run sc_process.StarcraftProcess."""
    raise NotImplementedError()

  @classmethod
  def all_subclasses(cls):
    """An iterator over all subclasses of `cls`."""
    for s in cls.__subclasses__():
      yield s
      for c in s.all_subclasses():
        yield c

  @classmethod
  def name(cls):
    return cls.__name__

  @classmethod
  def priority(cls):
    """None means this isn't valid. Run the one with the max priority."""
    return None

  def get_versions(self, containing=None):
    """Return a dict of all versions that can be run."""
    if containing is not None and containing not in VERSIONS:
      raise ValueError("Unknown game version: %s. Known versions: %s." % (
          containing, sorted(VERSIONS.keys())))
    return VERSIONS

  def _get_version(self, game_version):
    """Get the full details for the specified game version."""
    if isinstance(game_version, Version):
      if not game_version.game_version:
        raise ValueError(
            "Version '%r' supplied without a game version." % (game_version,))
      if (game_version.data_version and
          game_version.binary and
          game_version.build_version):
        return game_version
      # Some fields might be missing from serialized versions. Look them up.
      game_version = game_version.game_version
    if game_version.count(".") == 1:
      game_version += ".0"
    versions = self.get_versions(containing=game_version)
    return versions[game_version]
