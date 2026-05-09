#!/usr/bin/env python3
"""Convert flat AUP2 (1 scene, N objects on Layer 0) to scene-reference + layer architecture.

Input:  1 scene, N objects on Layer 0, each with 動画ファイル + 映像再生 effects.
Output: 1+N scenes, 3N objects:
  - scene.0 (main comp): 2N objects — シーン ref + 動画ファイル copy per source clip
  - scene.1..N (sub-scenes): N objects — 1 動画ファイル object each

Usage:
  python extensions/convert_flat_to_scene.py tests/fixtures/test2.aup2 -o output.aup2
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so 'from aup2_parser' works
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aup2_parser import AUP2Parser

import argparse
from collections import defaultdict
from copy import deepcopy

def _parse_source(input_path: Path):
    """Parse source AUP2 and extract scene.0 settings + N source objects."""
    parser = AUP2Parser.from_file(str(input_path))
    data = parser.parse()

    project = deepcopy(data.get("project", {}))
    scene0 = deepcopy(data.get("scene.0", {}))
    if not scene0:
        raise ValueError("Source file must contain a [scene.0] section")

    # Collect source objects sorted by numeric ID
    obj_keys = sorted(
        [k for k in data if k.startswith("object.")],
        key=lambda k: int(k.split(".")[1]),
    )
    if not obj_keys:
        raise ValueError("No objects found in source file")

    source_objects = []
    for key in obj_keys:
        obj = data[key]
        effects = deepcopy(obj.get("effects", {}))
        source_objects.append(
            {
                "layer": obj.get("layer", 0),
                "frame": obj.get("frame", [0, 0]),
                "effects": effects,
            }
        )

    return project, scene0, source_objects


def _find_effects(effects):
    """Find 動画ファイル and 映像再生 effects in an effects dict.

    Returns (movie_effect, video_playback_effect) where each may be None.
    """
    movie = None
    playback = None
    for _ek, ev in effects.items():
        name = ev.get("effect.name", "")
        if name == "動画ファイル":
            movie = ev
        elif name == "映像再生":
            playback = ev
    return movie, playback


def _build_output(project, scene0, source_objects):
    """Build the output dict with project + N+1 scenes + 3N objects."""
    output = {}
    N = len(source_objects)

    # --- project ---
    proj = deepcopy(project)
    proj["display.scene"] = 0
    output["project"] = proj

    # --- scene.0: main composition ---
    main_scene = deepcopy(scene0)
    main_scene["scene"] = 0
    main_scene["name"] = "主合成"
    output["scene.0"] = main_scene

    # --- sub-scenes scene.1..scene.N ---
    for i in range(N):
        sk = f"scene.{i + 1}"
        sd = deepcopy(scene0)
        sd["scene"] = i + 1
        sd["name"] = f"clip{i + 1}"
        output[sk] = sd

    # --- objects ---
    obj_id = 0

    # Main comp objects (scene.0): 2 per source clip
    for i, src in enumerate(source_objects):
        frame = src["frame"]
        start, end = frame[0], frame[-1]
        movie_effect, playback_effect = _find_effects(src["effects"])

        # Object A: シーン (scene reference) on Layer 0
        if playback_effect is not None:
            scene_eff = deepcopy(playback_effect)
            scene_eff["effect.name"] = "シーン"
        else:
            scene_eff = {}
            scene_eff["effect.name"] = "シーン"
        scene_eff["シーン"] = i + 1
        scene_eff["ループ再生"] = 0

        scene_obj = {
            "layer": 0,
            "frame": [start, end],
            "scene": 0,
            "effects": {"effect.0": scene_eff},
        }
        output[f"object.{obj_id}"] = scene_obj
        obj_id += 1

        # Object B: 動画ファイル full copy on Layer (i+1)
        vcopy_obj = {
            "layer": i + 1,
            "frame": [start, end],
            "scene": 0,
            "effects": deepcopy(src["effects"]),
        }
        output[f"object.{obj_id}"] = vcopy_obj
        obj_id += 1

    # Sub-scene objects (scene.1..scene.N): 1 each
    for i, src in enumerate(source_objects):
        frame = src["frame"]
        start, end = frame[0], frame[-1]
        dur = end - start

        sub_obj = {
            "layer": 0,
            "frame": [0, dur],
            "scene": i + 1,
            "effects": deepcopy(src["effects"]),
        }
        output[f"object.{obj_id}"] = sub_obj
        obj_id += 1

    return output, N


def _reconstruct_to_string(output_dict):
    """Reconstruct AUP2 string from dict with \\r\\n line endings."""
    parser = AUP2Parser.__new__(AUP2Parser)
    parser.aup2_content = None
    parser._init_fields()
    parser._line_ending = "\r\n"
    parser._trailing_newline = True
    parser.data = defaultdict(dict, output_dict)
    return parser.reconstruct()


def convert_flat_to_scene(input_path, output_path):
    """Main conversion entry point.

    Returns the number of source clips (N).
    """
    project, scene0, source_objects = _parse_source(input_path)
    output_dict, N = _build_output(project, scene0, source_objects)
    aup2_str = _reconstruct_to_string(output_dict)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Use newline='' so that \r\n written verbatim, not translated
    out.write_text(aup2_str, encoding="utf-8", newline="")

    return N


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Convert flat AUP2 (1 scene, all objects on Layer 0) "
        "to scene-reference + layer architecture."
    )
    ap.add_argument("input", type=Path, help="Source AUP2 file")
    ap.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output AUP2 file (default: <input>_converted.aup2)",
    )
    ap.add_argument(
        "--encoding", default="utf-8",
        help="File encoding (default: utf-8)",
    )
    args = ap.parse_args()

    inp = args.input
    if not inp.exists():
        print(f"Error: input file not found: {inp}", file=sys.stderr)
        sys.exit(1)

    if args.output is None:
        args.output = inp.with_stem(inp.stem + "_converted")

    print(f"Converting: {inp} → {args.output}")
    N = convert_flat_to_scene(inp, args.output)
    total_objects = 3 * N
    total_scenes = N + 1
    print(f"Done: {N} source clips → {total_scenes} scenes, {total_objects} objects")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
