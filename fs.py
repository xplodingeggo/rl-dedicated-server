"""Case-insensitive file lookup: the game's files are named for Windows, and Linux file systems are case sensitive."""
import os


def find(folder, *names):
    """-> the path folder/names[0]/names[1]/... with each part matched ignoring case. Parts that don't exist are
    returned as given, so opening the result fails with a clear error."""
    path = folder
    for name in names:
        exact = os.path.join(path, name)
        if not os.path.exists(exact) and os.path.isdir(path):
            hits = [f for f in os.listdir(path) if f.lower() == name.lower()]
            if hits:
                exact = os.path.join(path, sorted(hits)[0])
        path = exact
    return path
