# fork/

What belongs to this fork alone and is not meant to go upstream.

Everything outside this folder follows upstream's rules, so the tree can be
taken into [salitronic/eda-agent](https://github.com/salitronic/eda-agent) as
it is by leaving this folder behind. In particular, upstream's publication
rule (`tests/test_no_altium_internals_published.py`: no Altium program module
names, no crash addresses, no claim about running without a licensed Altium)
holds for the whole tree except here.

- `notes/` - this fork's working journals: the state of the deployment, the
  to-do list, shutdown and crash investigations, behaviour checks, design
  notes. They name Altium's modules and quote crash messages because that is
  what was investigated.

One feature outside this folder is also this fork's own and is listed in that
test by file: `sdk-symbols` (`src/eda_agent/sdk/symbols.py`), which reads the
scripting engine's table of names from the user's own Altium installation.
