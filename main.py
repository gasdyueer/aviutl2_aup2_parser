#!/usr/bin/env python3
"""AUP2 CLI — parse, validate, convert, and rebuild AviUtl AUP2 project files.

Zero external dependencies.  Uses only stdlib argparse.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from .aup2_parser import (
        AUP2Parser,
        AUP2ParseError,
        AUP2ValidationError,
        AUP2ReconstructionError,
        validate_aup2_file,
    )
except ImportError:
    from aup2_parser import (  # type: ignore[no-redef]
        AUP2Parser,
        AUP2ParseError,
        AUP2ValidationError,
        AUP2ReconstructionError,
        validate_aup2_file,
    )

# ── helpers ──────────────────────────────────────────────────────────

def _add_encoding(argparser: argparse.ArgumentParser) -> None:
    argparser.add_argument(
        '-e', '--encoding', default='utf-8',
        help='file encoding (default: utf-8)',
    )


def _die(msg: str, code: int = 1) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


# ── subcommand handlers ──────────────────────────────────────────────

def _cmd_parse(args: argparse.Namespace) -> None:
    parser = AUP2Parser.from_file(args.file, args.encoding)
    data = parser.parse()

    if args.include_records:
        output = parser.to_dict(include_records=True)
    else:
        output = data

    indent = None if args.no_pretty else 2
    json_str = json.dumps(output, indent=indent, ensure_ascii=False)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding=args.encoding) as fh:
            fh.write(json_str)
    else:
        print(json_str)


def _cmd_info(args: argparse.Namespace) -> None:
    parser = AUP2Parser.from_file(args.file, args.encoding)
    data = parser.parse()
    # get_summary() reads _metadata from self.data, but parse() only returns it.
    # Inject metadata so get_summary sees line_count and warnings.
    if '_metadata' in data:
        parser.data['_metadata'] = data['_metadata']
    summary = parser.get_summary()

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    print(f"File:         {args.file}")
    print(f"Scenes:       {summary['scenes']}")
    print(f"Objects:      {summary['objects']}")
    print(f"Sections:     {summary['total_sections']}")
    print(f"Has project:  {'yes' if summary['has_project'] else 'no'}")
    print(f"Lines:        {summary['parsing_line_count']}")
    print(f"Warnings:     {summary['warnings_count']}")

    layer_dist = summary.get('layer_distribution')
    if layer_dist:
        print("\nLayer distribution:")
        for layer in sorted(layer_dist):
            print(f"  Layer {layer}: {layer_dist[layer]} object(s)")


def _cmd_validate(args: argparse.Namespace) -> None:
    is_valid, messages = validate_aup2_file(args.file, args.encoding)

    if not args.quiet:
        for msg in messages:
            print(msg, file=sys.stderr)

    sys.exit(0 if is_valid else 1)


def _cmd_convert(args: argparse.Namespace) -> None:
    inp = Path(args.input)
    outp = Path(args.output)
    inp_suffix = inp.suffix.lower()
    out_suffix = outp.suffix.lower()

    if inp_suffix == '.aup2' and out_suffix != '.aup2':
        # AUP2 → JSON (flat format, compatible with reconstruct_from_json)
        parser = AUP2Parser.from_file(args.input, args.encoding)
        data = parser.parse()
        outp.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding=args.encoding) as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    elif inp_suffix != '.aup2' and out_suffix == '.aup2':
        # JSON → AUP2
        content = AUP2Parser.reconstruct_from_json(args.input, args.encoding)
        outp.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding=args.encoding) as fh:
            fh.write(content)

    elif inp_suffix == '.aup2' and out_suffix == '.aup2':
        # AUP2 → AUP2 (rebuild pass-through)
        parser = AUP2Parser.from_file(args.input, args.encoding)
        parser.parse()
        parser.save_to_file(args.output, args.encoding)

    else:
        _die("Cannot determine conversion direction from extensions."
             "  Supported: .aup2 → .json, .json → .aup2")


def _cmd_rebuild(args: argparse.Namespace) -> None:
    original_bytes = Path(args.file).read_bytes()
    original_hash = hashlib.sha256(original_bytes).hexdigest()

    parser = AUP2Parser.from_file(args.file, args.encoding)
    parser.parse()
    reconstructed = parser.reconstruct()
    reconstructed_bytes = reconstructed.encode(args.encoding)
    reconstructed_hash = hashlib.sha256(reconstructed_bytes).hexdigest()

    match = original_hash == reconstructed_hash

    print(f"Original file:   {args.file}")
    print(f"Encoding:        {args.encoding}")
    print(f"Original SHA256: {original_hash}")
    print(f"Rebuilt  SHA256: {reconstructed_hash}")
    print(f"Round-trip:      {'YES' if match else 'NO'}")

    if args.output:
        parser.save_to_file(args.output, args.encoding)
        print(f"Saved rebuilt to: {args.output}")

    if not match:
        sys.exit(1)


# ── argument parser ──────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(
        prog='aup2',
        description='Parse, validate, convert, and rebuild AviUtl AUP2 project files.',
    )
    sub = top.add_subparsers(dest='command', required=True, title='subcommands')

    # parse
    p = sub.add_parser('parse', help='parse AUP2 file to JSON')
    p.add_argument('file', help='AUP2 file to parse')
    _add_encoding(p)
    p.add_argument('-o', '--output', help='write JSON to file instead of stdout')
    p.add_argument('--no-pretty', action='store_true',
                   help='output compact JSON')
    p.add_argument('--include-records', action='store_true',
                   help='include _line_records for round-trip state persistence')

    # info
    p = sub.add_parser('info', help='show AUP2 file structure summary')
    p.add_argument('file', help='AUP2 file to inspect')
    _add_encoding(p)
    p.add_argument('--json', action='store_true',
                   help='output as machine-readable JSON')

    # validate
    p = sub.add_parser('validate', help='validate AUP2 file integrity')
    p.add_argument('file', help='AUP2 file to validate')
    _add_encoding(p)
    p.add_argument('--quiet', action='store_true',
                   help='only return exit code')

    # convert
    p = sub.add_parser('convert', help='convert between AUP2 and JSON')
    p.add_argument('input', help='input file (.aup2 or .json)')
    p.add_argument('output', help='output file (.aup2 or .json)')
    _add_encoding(p)

    # rebuild
    p = sub.add_parser('rebuild', help='round-trip rebuild verification')
    p.add_argument('file', help='AUP2 file to rebuild')
    _add_encoding(p)
    p.add_argument('-o', '--output', help='write rebuilt AUP2 to file')

    return top


# ── entry point ──────────────────────────────────────────────────────

_HANDLERS = {
    'parse':    _cmd_parse,
    'info':     _cmd_info,
    'validate': _cmd_validate,
    'convert':  _cmd_convert,
    'rebuild':  _cmd_rebuild,
}


# On Windows, console may use a narrow code page that cannot encode CJK characters.
# Reconfigure to UTF-8 when possible so JSON output and error messages work.
for _for_stream in (sys.stdout, sys.stderr):
    try:
        _for_stream.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass
def main() -> None:
    """Entry point for the AUP2 CLI."""
    argparser = _build_parser()
    args = argparser.parse_args()

    handler = _HANDLERS.get(args.command)
    if handler is None:
        argparser.print_help()
        sys.exit(1)

    try:
        handler(args)
    except (AUP2ParseError, AUP2ValidationError, AUP2ReconstructionError) as e:
        _die(str(e))
    except FileNotFoundError as e:
        _die(f"file not found: {e.filename}")


if __name__ == '__main__':
    main()
