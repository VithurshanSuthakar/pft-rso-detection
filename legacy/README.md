# Original source snapshots

These are byte-identical copies of the two supplied Python source files, renamed
to `.py.txt` so they are reference text rather than package entry points:

| File | SHA-256 of the original bytes |
| --- | --- |
| [main.py.txt](main.py.txt) | `1b5321846327751f1c38fcc206b869f1daba29c9e88ee03ae9c15c2d56504084` |
| [score_calculation.py.txt](score_calculation.py.txt) | `841f705c31fd5786416be142581ead118af66823e8459ddcba999488da0e903e` |

Use `pft-detect` or `python -m pft_rso` for the maintained detector. The historical
main script contains import-time file writes and GUI calls. The scorer has known
matching errors and must not be used as evidence of detection accuracy.

See [changes from source](../docs/changes-from-source.md) for the migration details
and [paper/provenance](../docs/paper-and-provenance.md) for scientific scope.

