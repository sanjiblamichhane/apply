# Backups and moving

```sh
apply export --out backup.json        # everything you made, as apply-export/1 JSON
apply import backup.json              # restore it, here or on another install
```

The export holds your settings, profiles, opportunities, applications (with their stages, history and
submissions), every finished version of each document (with its claim warnings and review), saved answers,
sources, searches and matches. A test checks that every new table is either exported or listed with the reason
it isn't.

Left out on purpose:

- sign-in sessions and API tokens: they're secrets, so make new ones;
- briefings and PDFs: they're made again from the rest;
- Auto's runs (and the screenshots of runs from when apply still sent): a run's outcome is kept as its submission.

Importing the same file again adds only what's new. An import turns a search's Auto switch off, and never
un-pauses Auto: that's something you turn on again yourself.
