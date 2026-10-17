# Category state and trash

`user_data/snips/categories.json` is the authoritative ordered list:

```json
[
  {"name": "Python", "pinned": false, "deleted": false},
  {"name": "PySide6", "pinned": true, "deleted": false}
]
```

Old string lists are validated completely and converted with an atomic write on
load. Invalid records, unsafe names, mixed formats and case-insensitive duplicate
names are rejected without rewriting the file. Only active directories are
ensured. Directory discovery does not add or reactivate categories.

Pinned active categories appear first, retaining JSON order within both groups.
Pin/unpin only writes the JSON. The Recent snippets button is not a category and
has no category context menu.

After confirmation, delete renames `snips/<name>` to `trash/categories/<name>` as
one directory, sets `deleted` to true and `pinned` to false, and refreshes search.
Restore validates the category's snippets, renames the directory back, clears
`deleted`, and refreshes search. Restored categories are unpinned and keep their
position in the JSON list. Existing destinations are never merged or overwritten.
The name remains reserved while deleted. Individual snippet trash remains in
`trash/snips/<uuid>`; a snippet whose category is deleted can be restored after
restoring that category, or through the library API into another active category.

The settings deleted-items dialog has separate category and snippet lists.
Permanent category deletion requires another confirmation. It removes the trash
directory first, then removes the JSON record. A filesystem failure keeps the
record; deletion can be retried. If only the final metadata write fails, the
record remains visible in trash and repeating permanent deletion removes it.
Backup validation requires deleted category directories to exist, so finalize
such a pending metadata removal before making a backup.

Caught metadata failures after a move trigger a move back. If rollback itself
fails, a specific error asks the user to stop editing and recover the category
from the reported normal/trash locations; the data is not discarded. As with
existing library operations, this supports one writer and is not a transaction
against process termination or power loss. A failed permanent filesystem removal
may already have removed some files; permanent deletion is intentionally
irreversible. Symlinks and junctions, including ancestors and category contents,
are rejected before category moves or recursive deletion.

See [cloud-backup.md](cloud-backup.md) for snapshot compatibility and category
trash backup/restore behavior.
