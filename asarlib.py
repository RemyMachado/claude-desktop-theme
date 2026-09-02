"""Read and rewrite Electron .asar archives.

Layout:  [16-byte framing][JSON header, padded to 4 bytes][file payloads]
The header is a directory tree; each file records size, offset into the payload
region, and a SHA256 integrity record. Changing any file's length shifts every
later offset, so a modified archive must be rebuilt whole.
"""
import json, struct, hashlib
from collections import OrderedDict

BLOCK = 4 * 1024 * 1024


def _pad(n):
    return (4 - (n % 4)) % 4


def read_header(path):
    with open(path, "rb") as f:
        word0, _w1, _w2, strlen = struct.unpack("<IIII", f.read(16))
        if word0 != 4:
            raise ValueError("not an asar archive")
        header = json.loads(f.read(strlen).decode("utf8"), object_pairs_hook=OrderedDict)
    return header, 16 + strlen + _pad(strlen)


def walk(node, path=""):
    """Yield (asar_path, entry) for every file, in header order."""
    for name, entry in node.get("files", {}).items():
        p = f"{path}/{name}"
        if "files" in entry:
            yield from walk(entry, p)
        else:
            yield p, entry


def integrity(data):
    return OrderedDict([
        ("algorithm", "SHA256"),
        ("hash", hashlib.sha256(data).hexdigest()),
        ("blockSize", BLOCK),
        ("blocks", [hashlib.sha256(data[i:i + BLOCK]).hexdigest()
                    for i in range(0, len(data), BLOCK)] or
                   [hashlib.sha256(b"").hexdigest()]),
    ])


def repack(src, dst, replacements):
    """Copy src to dst, substituting {asar_path: bytes}.

    Two things must be preserved or the archive grows / breaks:
      * entries with no 'offset' are unpacked files living in app.asar.unpacked/
        and carry no payload here;
      * identical files are deduplicated by pointing several entries at one
        offset (this build shares font payloads across five renderer bundles),
        so shared payloads must stay shared.
    """
    header, base = read_header(src)
    seen = set()
    emitted = {}                      # original offset -> (new offset, size)
    payload = bytearray()

    with open(src, "rb") as fin:
        for path, entry in walk(header):
            if "offset" not in entry:
                continue
            old_off = int(entry["offset"])

            if path in replacements:
                data = replacements[path]
                seen.add(path)
                entry["offset"] = str(len(payload))
                entry["size"] = len(data)
                if "integrity" in entry:
                    entry["integrity"] = integrity(data)
                payload += data
                continue              # never share a rewritten payload

            if old_off in emitted:     # deduplicated copy: point at the same bytes
                new_off, size = emitted[old_off]
                entry["offset"] = str(new_off)
                entry["size"] = size
                continue

            fin.seek(base + old_off)
            data = fin.read(entry["size"])
            if len(data) != entry["size"]:
                raise ValueError(f"short read for {path}")
            new_off = len(payload)
            emitted[old_off] = (new_off, len(data))
            entry["offset"] = str(new_off)
            payload += data            # integrity unchanged, so leave it alone

    missing = set(replacements) - seen
    if missing:
        raise ValueError(f"replacement paths not found in archive: {missing}")

    blob = json.dumps(header, separators=(",", ":")).encode("utf8")
    pad = _pad(len(blob))
    with open(dst, "wb") as fout:
        fout.write(struct.pack("<IIII", 4, 8 + len(blob) + pad,
                               4 + len(blob) + pad, len(blob)))
        fout.write(blob)
        fout.write(b"\0" * pad)
        fout.write(payload)
    return dst


def read_file(path, asar_path):
    header, base = read_header(path)
    for p, entry in walk(header):
        if p == asar_path:
            if "offset" not in entry:
                raise KeyError(f"{asar_path} is unpacked")
            with open(path, "rb") as f:
                f.seek(base + int(entry["offset"]))
                return f.read(entry["size"])
    raise KeyError(asar_path)
