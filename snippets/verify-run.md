The run ends with a recap line for the host. `failed=0` and `unreachable=0` mean every stage finished, and the last stage only finishes once Komodo reports every one of the host's Stacks as running.

In Komodo's UI, open *Resources > Servers*. The host shows as connected.

Open *Resources > Stacks* and filter by that Server. Each Stack shows as *Running*.

If the run stopped instead, its last message names the stage and what it stopped at. Fix the cause and run it again. Every stage is safe to repeat.
