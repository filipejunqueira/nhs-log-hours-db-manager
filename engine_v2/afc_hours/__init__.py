"""afc_hours -- AfC part-time extra-hours engine (v2).

Four load-bearing modules, one-way dependency graph:

    rules  <-  core  <-  emit
                 \\__  money   (reads core's result; never writes the JSON)

`rules` is the law (constants only). `core` is Part (i): the deterministic
hours computation that produces the website JSON, a pure function of the CSV.
`money` is Part (ii): pay figures and variants, kept entirely off the JSON path.
"""
