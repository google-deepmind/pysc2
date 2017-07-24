# StarCraft II Maps

## Map config

SC2Map files are what is used by the SC2 game, but they can be used differently,
and those differences are defined in our map configs. The config gives
information like how long the episodes last, how many players it can play, and
how to score it.

To create your own map config, just subclass the base Map class and override
some of the settings. The most important is to define the directory and filename
for the SC2Map. Any Map subclass will be automatically picked up as long as it's
imported somewhere.

## DeepMind Mini-Games

The [mini-games](mini_games.md) are designed to be single-player, fixed length
and exercise different aspects of the game. They expose a score/reward which
lets the agent know how well it is doing. The score should differentiate poor
agents (eg random) from good agents.

## Ladder

[Ladder maps](http://wiki.teamliquid.net/starcraft2/Maps/Ladder_Maps/Legacy_of_the_Void)
are the maps played by human players on Battle.net. There are just a handful
active at a time. Every few months a new season starts bringing a new set of
maps.

Some of the maps have suffixes LE or TE. LE means Ladder Edition. These are
community maps that were edited by Blizzard for bugs and made ready for the
ladder pool. TE means Tournament Edition. These maps were used in tournaments.

They are all multiplayer maps with fairly long time limits.

## Melee

These are maps made specifically for machine learning. They resemble
ladder maps in format, but may be smaller sizes and aren't necessarily balanced
for high level play.

The **Flat** maps have no special features on the terrain, encouraging easy
attacking. The number specifies the map size.

The **Simple** maps are more normal with expansions, ramps, and lanes of attack,
but are smaller than normal ladder maps. The number specifies the map size.
