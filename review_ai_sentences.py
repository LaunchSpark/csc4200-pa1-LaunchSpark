#!/usr/bin/env python3
"""
AI Sentence Review Tool

Extracts every complete sentence containing "AI " from specified files
(or automatically detects markdown/text/chunk files) and provides an
interactive terminal interface to keep or delete sentences:

  [← Left Arrow]  : Delete sentence
  [→ Right Arrow] : Keep sentence
  [↑ Up Arrow] / u: Undo previous action
  [s]             : Skip sentence
  [q]             : Save & Quit
"""

import sys
import os
import re
import glob
import json
import shutil
import select
import argparse
import textwrap

# ANSI color escape codes
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_DIM     = "\033[2m"
C_RED     = "\033[91m"
C_GREEN   = "\033[92m"
C_YELLOW  = "\033[93m"
C_BLUE    = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN    = "\033[96m"
C_WHITE   = "\033[97m"
C_BG_RED  = "\033[41m"
C_BG_GRN  = "\033[42m"
C_ULINE   = "\033[4m"


def supports_raw_terminal():
    """Check if standard input and output support raw terminal interaction."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def read_key():
    """
    Read a single keypress or ANSI escape sequence from the terminal in raw mode.
    Uses unbuffered OS-level reads to reliably capture multi-byte arrow key sequences.
    """
    if not supports_raw_terminal():
        line = sys.stdin.readline()
        if not line:
            return 'q'
        ch = line.strip().lower()
        if ch in ('left', 'l', 'd', 'del', 'n', '<'):
            return 'left'
        elif ch in ('right', 'r', 'k', 'y', 'enter', '>'):
            return 'right'
        elif ch in ('undo', 'u', 'up'):
            return 'up'
        elif ch in ('skip', 's'):
            return 's'
        elif ch in ('quit', 'q', 'exit'):
            return 'q'
        return ch

    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # Unbuffered read of up to 32 bytes
        raw_bytes = os.read(fd, 32)
        # If bare escape byte received, check if trailing bytes follow immediately
        if raw_bytes == b'\x1b':
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                raw_bytes += os.read(fd, 31)

        # Match arrow keys (both standard ANSI and application cursor mode)
        if raw_bytes in (b'\x1b[D', b'\x1bOD'):
            return 'left'
        elif raw_bytes in (b'\x1b[C', b'\x1bOC'):
            return 'right'
        elif raw_bytes in (b'\x1b[A', b'\x1bOA'):
            return 'up'
        elif raw_bytes in (b'\x1b[B', b'\x1bOB'):
            return 'down'
        elif raw_bytes == b'\x03':  # Ctrl+C
            return 'ctrl_c'
        elif raw_bytes == b'\x04':  # Ctrl+D
            return 'ctrl_d'
        elif raw_bytes in (b'\x7f', b'\x08'):
            return 'backspace'
        elif raw_bytes in (b'\r', b'\n'):
            return 'enter'
        elif raw_bytes == b' ':
            return 'space'
        elif raw_bytes == b'\x1b':
            return 'esc'

        try:
            return raw_bytes.decode('utf-8', errors='ignore')
        except Exception:
            return ''
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def parse_document_blocks(text):
    """
    Parse text into logical blocks, separating tables and headings,
    and merging accidental mid-sentence line breaks.
    """
    raw_lines = text.splitlines()
    blocks = []
    curr = []
    in_table = False

    for line in raw_lines:
        s = line.strip()
        if not s:
            if curr:
                blocks.append("\n".join(curr))
                curr = []
            in_table = False
            continue

        # Keep markdown table rows separate
        if s.startswith('|'):
            if curr and not in_table:
                blocks.append("\n".join(curr))
                curr = []
            in_table = True
            blocks.append(s)
            continue
        else:
            in_table = False

        # Keep markdown headers separate
        if s.startswith('#'):
            if curr:
                blocks.append("\n".join(curr))
                curr = []
            blocks.append(s)
            continue

        curr.append(s)

    if curr:
        blocks.append("\n".join(curr))

    # Merge paragraphs that broke mid-sentence across empty lines
    merged_blocks = []
    for b in blocks:
        if merged_blocks:
            prev = merged_blocks[-1].strip()
            # If previous block did not end with terminal punctuation
            # and current doesn't start with heading or list bullet or table
            # and current starts with lowercase or continuation word
            if (not prev.endswith(('.', '!', '?', ':', '|', '#', '```', '---')) and
                not re.match(r'^(?:[#|]|\-{3,}|`{3}|[-*+]\s+|\d+\.\s+)', b.strip()) and
                (b.strip()[0].islower() or b.strip().startswith(('script', 'and', 'or', 'which', 'that')))):
                merged_blocks[-1] = prev + " " + b.strip()
                continue
        merged_blocks.append(b)

    return merged_blocks


def extract_sentences_from_text(text, source_path, query="AI "):
    """
    Extract complete sentences containing `query` from text.
    Returns a list of dicts: {'sentence': ..., 'source': ..., 'raw': ..., 'tag': ...}
    """
    blocks = parse_document_blocks(text)
    results = []

    for b in blocks:
        if query not in b:
            continue

        # Check if block is a table row
        if b.strip().startswith('|'):
            row_clean = re.sub(r'^[|\s]+|[|\s]+$', '', b.strip())
            cells = [c.strip() for c in row_clean.split('|')]
            matching_cells = [c for c in cells if query in c]
            cell_text = " | ".join(matching_cells) if matching_cells else row_clean
            results.append({
                'sentence': cell_text,
                'source': source_path,
                'raw': b.strip(),
                'tag': 'Table Row',
            })
            continue

        # Check if block is a markdown header
        if b.strip().startswith('#'):
            h_text = re.sub(r'^\#{1,6}\s*', '', b.strip())
            if query in h_text:
                results.append({
                    'sentence': h_text,
                    'source': source_path,
                    'raw': b.strip(),
                    'tag': 'Heading',
                })
            continue

        # Split on list items if block contains a list
        items = re.split(r'\n(?=[-*+]\s+|\d+\.\s+)', b)
        for item in items:
            item_raw = item.strip()
            # Clean leading bullet markers
            item_clean = re.sub(r'^[-*+]\s+|\d+\.\s+', '', item_raw)

            # Collapse multi-line whitespace within the sentence
            item_clean = re.sub(r'\s+', ' ', item_clean)

            # Sentence splitting: punctuation followed by space and capital/number/quote
            pattern = r'(?<!\be\.g)(?<!\bi\.e)(?<!\betc)(?<!\bvs)(?<!\bDr)(?<!\bMr)(?<!\bMs)(?<=[.!?])\s+(?=[A-Z0-9"\'“‘])'
            raw_sents = re.split(pattern, item_clean)

            for s in raw_sents:
                s_strip = s.strip()
                if query in s_strip:
                    cleaned_display = s_strip.replace(r'\_', '_')
                    results.append({
                        'sentence': cleaned_display,
                        'source': source_path,
                        'raw': s_strip,
                        'tag': 'Sentence',
                    })

    return results


def extract_from_jsonl(filepath, query="AI "):
    """Extract sentences containing `query` from a jsonl chunk file."""
    results = []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line_no, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str or query not in line_str:
                continue
            try:
                data = json.loads(line_str)
                text = data.get('text', '')
                doc = data.get('doc', os.path.basename(filepath))
                chunk_id = data.get('chunk_id', line_no)
                if query in text:
                    for s in extract_sentences_from_text(text, f"{doc} (chunk {chunk_id})", query):
                        results.append(s)
            except json.JSONDecodeError:
                for s in extract_sentences_from_text(line_str, f"{filepath}:{line_no}", query):
                    results.append(s)
    return results


def scan_file(filepath, query="AI "):
    """Scan a single file based on its extension."""
    if not os.path.isfile(filepath):
        return []
    if filepath.endswith('.chunks.jsonl') or filepath.endswith('.jsonl'):
        return extract_from_jsonl(filepath, query)
    elif filepath.endswith('.json'):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
            texts = []
            if isinstance(data, dict) and 'texts' in data and isinstance(data['texts'], list):
                for item in data['texts']:
                    t = item.get('text', '')
                    if query in t:
                        texts.append(t)
            elif isinstance(data, (dict, list)):
                dump = json.dumps(data)
                if query in dump:
                    texts.append(dump)
            res = []
            for t in texts:
                res.extend(extract_sentences_from_text(t, filepath, query))
            return res
        except Exception:
            return []
    else:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return extract_sentences_from_text(content, filepath, query)
        except Exception as e:
            print(f"Warning: could not read {filepath}: {e}", file=sys.stderr)
            return []


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def discover_default_files():
    """Discover default markdown/text files in parsed_output/ or project folder."""
    files = []
    # Search paths: current working directory, then script directory
    search_dirs = [os.getcwd()]
    if SCRIPT_DIR not in search_dirs:
        search_dirs.append(SCRIPT_DIR)

    for base in search_dirs:
        parsed_out = os.path.join(base, 'parsed_output')
        if os.path.isdir(parsed_out):
            md_files = sorted(glob.glob(os.path.join(parsed_out, '*.md')))
            txt_files = sorted(glob.glob(os.path.join(parsed_out, '*.txt')))
            for f in md_files + txt_files:
                if f not in files:
                    files.append(f)

        for f in sorted(glob.glob(os.path.join(base, '*.md'))):
            if f not in files and not f.endswith('review_ai_sentences.py'):
                files.append(f)

    return files


def deduplicate_sentences(sentence_list):
    """
    Group identical sentences together to avoid reviewing duplicates multiple times.
    """
    seen = {}
    ordered = []
    for item in sentence_list:
        s_text = item['sentence']
        if s_text in seen:
            entry = seen[s_text]
            if item['source'] not in entry['sources']:
                entry['sources'].append(item['source'])
            entry['count'] += 1
        else:
            entry = {
                'sentence': s_text,
                'sources': [item['source']],
                'count': 1,
                'raw': item['raw'],
                'tag': item.get('tag', 'Sentence'),
            }
            seen[s_text] = entry
            ordered.append(entry)
    return ordered


def format_highlighted_sentence(sentence, query, width):
    """Format and wrap sentence, highlighting query in bold yellow underline."""
    usable_width = max(30, width - 8)
    wrapped_lines = textwrap.wrap(sentence, width=usable_width)
    if not wrapped_lines:
        wrapped_lines = [""]

    highlight_ansi = f"{C_BOLD}{C_YELLOW}{C_ULINE}{query}{C_RESET}"
    highlighted_lines = [line.replace(query, highlight_ansi) for line in wrapped_lines]
    return highlighted_lines


def render_screen(sentence_item, index, total, decisions, feedback="", query="AI "):
    """Render the full interactive review screen in the terminal."""
    term_width, term_height = shutil.get_terminal_size((80, 24))
    width = min(term_width, 100)

    # Clear screen and move cursor to top-left
    sys.stdout.write("\033[2J\033[H")

    # Counts
    kept_count = sum(1 for d in decisions.values() if d == 'keep')
    del_count = sum(1 for d in decisions.values() if d == 'delete')
    remaining = total - len(decisions)

    # Progress bar
    bar_width = max(10, width - 45)
    pct = int((index / total) * 100) if total > 0 else 100
    filled = int(bar_width * (index / total)) if total > 0 else bar_width
    bar = f"{C_CYAN}{'█' * filled}{C_DIM}{'░' * (bar_width - filled)}{C_RESET}"

    # Header Box
    border = "═" * (width - 2)
    header = [
        f"{C_BOLD}{C_CYAN}╔{border}╗{C_RESET}",
        f"{C_BOLD}{C_CYAN}║{C_RESET} {C_WHITE}{C_BOLD}AI SENTENCE REVIEW TOOL{C_RESET}"
        f"  {C_RED}[← / d] Delete{C_RESET}  │  {C_GREEN}[→ / k / Enter] Keep{C_RESET}"
        f"{' ' * max(0, width - 66)}{C_BOLD}{C_CYAN}║{C_RESET}",
        f"{C_BOLD}{C_CYAN}╚{border}╝{C_RESET}",
    ]
    sys.stdout.write("\n".join(header) + "\n\n")

    # Progress & Stats
    print(f" {C_BOLD}Progress:{C_RESET} [{bar}] {pct:>3}%  (Sentence {index + 1} of {total})")
    print(f" {C_BOLD}Status:  {C_RESET} {C_GREEN}● Kept: {kept_count}{C_RESET}   "
          f"{C_RED}● Deleted: {del_count}{C_RESET}   "
          f"{C_DIM}● Remaining: {remaining}{C_RESET}\n")

    # Source Info
    sources_str = ", ".join(sentence_item['sources'])
    if len(sources_str) > width - 15:
        sources_str = sources_str[:width - 18] + "..."
    count_badge = f" ({sentence_item['count']} occurrences)" if sentence_item['count'] > 1 else ""
    tag_name = sentence_item.get('tag', 'Sentence')
    tag_color = C_YELLOW if tag_name in ('Heading', 'Table Row') else C_DIM
    tag_badge = f" {tag_color}[{tag_name}]{C_RESET}"

    print(f" {C_DIM}Source:{C_RESET}   {C_CYAN}{sources_str}{count_badge}{tag_badge}{C_RESET}\n")

    # Sentence Card Box
    card_border = "─" * (width - 4)
    print(f"  {C_DIM}╭{card_border}╮{C_RESET}")
    print(f"  {C_DIM}│{' ' * (width - 4)}│{C_RESET}")

    wrapped_lines = format_highlighted_sentence(sentence_item['sentence'], query, width)
    for line in wrapped_lines:
        plain_line = re.sub(r'\033\[[0-9;]*m', '', line)
        padding = max(0, (width - 4) - 4 - len(plain_line))
        print(f"  {C_DIM}│{C_RESET}   {line}{' ' * padding} {C_DIM}│{C_RESET}")

    print(f"  {C_DIM}│{' ' * (width - 4)}│{C_RESET}")
    print(f"  {C_DIM}╰{card_border}╯{C_RESET}\n")

    # Feedback message from previous action
    if feedback:
        print(f"  {feedback}\n")
    else:
        print("")

    # Control Bar
    ctrl_border = "─" * width
    print(f"{C_DIM}{ctrl_border}{C_RESET}")
    print(f" {C_RED}{C_BOLD}[← / d]{C_RESET} {C_RED}DELETE{C_RESET}   "
          f"{C_GREEN}{C_BOLD}[→ / k / Space / Enter]{C_RESET} {C_GREEN}KEEP{C_RESET}   "
          f"{C_YELLOW}{C_BOLD}[↑ / u]{C_RESET} Undo   "
          f"{C_DIM}[s] Skip   [q] Save & Exit{C_RESET}")
    print(f"{C_DIM}{ctrl_border}{C_RESET}")
    sys.stdout.flush()


def interactive_review(sentences, query="AI "):
    """Run the interactive review loop."""
    if not sentences:
        print(f"\n{C_YELLOW}No sentences found containing \"{query}\".{C_RESET}")
        return [], []

    total = len(sentences)
    current_idx = 0
    decisions = {}
    feedback = ""
    history = []

    while current_idx < total:
        item = sentences[current_idx]
        render_screen(item, current_idx, total, decisions, feedback, query)
        feedback = ""

        key = read_key()

        # Handle Left Arrow (Delete)
        if key in ('left', 'd', 'D', 'a', 'A', 'n', 'N'):
            decisions[current_idx] = 'delete'
            history.append(current_idx)
            feedback = f"{C_BG_RED}{C_WHITE}{C_BOLD} ✗ DELETED {C_RESET} {C_RED}Marked for removal{C_RESET}"
            current_idx += 1

        # Handle Right Arrow (Keep)
        elif key in ('right', 'k', 'K', 'l', 'L', 'y', 'Y', 'enter', 'space'):
            decisions[current_idx] = 'keep'
            history.append(current_idx)
            feedback = f"{C_BG_GRN}{C_WHITE}{C_BOLD} ✓ KEPT {C_RESET} {C_GREEN}Sentence saved{C_RESET}"
            current_idx += 1

        # Handle Undo
        elif key in ('up', 'u', 'U', 'backspace'):
            if history:
                prev_idx = history.pop()
                if prev_idx in decisions:
                    del decisions[prev_idx]
                current_idx = prev_idx
                feedback = f"{C_YELLOW}↺ Undid previous action{C_RESET}"
            else:
                feedback = f"{C_DIM}Already at the beginning.{C_RESET}"

        # Handle Skip
        elif key in ('down', 's', 'S'):
            feedback = f"{C_DIM}Skipped sentence.{C_RESET}"
            current_idx += 1

        # Handle Quit
        elif key in ('q', 'Q', 'ctrl_c'):
            print(f"\n{C_YELLOW}Exiting early... Saving decisions made so far.{C_RESET}")
            break

        # Handle bare Escape key
        elif key == 'esc':
            feedback = f"{C_YELLOW}Press [q] to save & quit, or use [←] Delete / [→] Keep.{C_RESET}"

    kept = []
    deleted = []
    for idx, item in enumerate(sentences):
        decision = decisions.get(idx)
        if decision == 'keep':
            kept.append(item)
        elif decision == 'delete':
            deleted.append(item)

    return kept, deleted


def save_results(kept, deleted, out_kept, out_del):
    """Save kept and deleted sentences to disk."""
    if out_kept:
        with open(out_kept, 'w', encoding='utf-8') as f:
            if kept:
                for i, item in enumerate(kept, 1):
                    sources_str = ", ".join(item['sources'])
                    f.write(f"# Sentence {i} [Source: {sources_str}]\n")
                    f.write(f"{item['sentence']}\n\n")
            else:
                f.write("# (No sentences kept)\n")

    if out_del:
        with open(out_del, 'w', encoding='utf-8') as f:
            if deleted:
                for i, item in enumerate(deleted, 1):
                    sources_str = ", ".join(item['sources'])
                    f.write(f"# Sentence {i} [Source: {sources_str}]\n")
                    f.write(f"{item['sentence']}\n\n")
            else:
                f.write("# (No sentences deleted)\n")


def remove_deleted_from_files(deleted_items):
    """Optionally remove deleted sentences from original files (with .bak backup)."""
    by_file = {}
    for item in deleted_items:
        for src in item['sources']:
            if '(' in src or ':' in src:
                src_path = src.split('(')[0].strip()
                if not os.path.isfile(src_path):
                    continue
            else:
                src_path = src
            if os.path.isfile(src_path):
                by_file.setdefault(src_path, set()).add(item['sentence'])
                by_file[src_path].add(item['raw'])

    modified = []
    for fpath, sents_to_remove in by_file.items():
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = content
            removed_count = 0
            for s in sents_to_remove:
                if s in new_content:
                    new_content = re.sub(r'[-*+]\s*' + re.escape(s) + r'\s*\n?', '', new_content)
                    new_content = new_content.replace(s, '')
                    removed_count += 1

            if new_content != content:
                bak_path = fpath + ".bak"
                with open(bak_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                modified.append((fpath, removed_count))
        except Exception as e:
            print(f"Error modifying {fpath}: {e}", file=sys.stderr)

    return modified


def main():
    parser = argparse.ArgumentParser(
        description="Grab every complete sentence containing 'AI ' and review each with Left (Delete) and Right (Keep)."
    )
    parser.add_argument(
        'paths',
        nargs='*',
        help="Files or directories to scan. Defaults to parsed_output/ and local markdown files if omitted."
    )
    parser.add_argument(
        '-q', '--query',
        default="AI ",
        help="Text query to search for (default: 'AI ')."
    )
    parser.add_argument(
        '-o', '--out',
        default="kept_ai_sentences.txt",
        help="Output file for kept sentences (default: kept_ai_sentences.txt)."
    )
    parser.add_argument(
        '--del-out',
        default="deleted_ai_sentences.txt",
        help="Output file for deleted sentences (default: deleted_ai_sentences.txt)."
    )
    parser.add_argument(
        '--no-dedup',
        action='store_true',
        help="Do not deduplicate identical sentences across files."
    )
    parser.add_argument(
        '--in-place',
        action='store_true',
        help="Automatically remove deleted sentences from the source files (creates .bak backups)."
    )
    parser.add_argument(
        '--include-json',
        action='store_true',
        help="Also scan raw .json files in directories (can contain duplicates)."
    )

    args = parser.parse_args()

    # Determine files to scan
    target_files = []
    if args.paths:
        for p in args.paths:
            if os.path.isfile(p):
                target_files.append(p)
            elif os.path.isdir(p):
                exts = ['*.md', '*.txt', '*.chunks.jsonl']
                if args.include_json:
                    exts.append('*.json')
                for ext in exts:
                    target_files.extend(glob.glob(os.path.join(p, ext)))
            else:
                matches = glob.glob(p)
                if matches:
                    target_files.extend(matches)
                else:
                    print(f"Warning: path not found '{p}'", file=sys.stderr)
    else:
        target_files = discover_default_files()

    if not target_files:
        print(f"{C_RED}No files found to scan.{C_RESET}")
        print("Please specify a file or directory: python3 review_ai_sentences.py <path>")
        sys.exit(1)

    print(f"{C_CYAN}Scanning {len(target_files)} file(s) for sentences containing \"{args.query}\"...{C_RESET}")
    raw_sentences = []
    for f in target_files:
        found = scan_file(f, query=args.query)
        raw_sentences.extend(found)

    if not raw_sentences:
        print(f"{C_YELLOW}No sentences found containing \"{args.query}\".{C_RESET}")
        sys.exit(0)

    # Deduplicate or structure
    if args.no_dedup:
        sentences = [{
            'sentence': item['sentence'],
            'sources': [item['source']],
            'count': 1,
            'raw': item['raw'],
            'tag': item.get('tag', 'Sentence')
        } for item in raw_sentences]
    else:
        sentences = deduplicate_sentences(raw_sentences)

    print(f"{C_GREEN}Found {len(sentences)} unique sentences (from {len(raw_sentences)} total occurrences).{C_RESET}")
    print(f"Press Enter to launch interactive review (or Ctrl+C to cancel)...", end="")
    try:
        if supports_raw_terminal():
            input()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(0)

    # Launch interactive review
    kept, deleted = interactive_review(sentences, query=args.query)

    # Save outputs
    save_results(kept, deleted, args.out, args.del_out)

    # Summary
    print(f"\n{C_BOLD}{'=' * 60}{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}                 REVIEW SUMMARY{C_RESET}")
    print(f"{C_BOLD}{'=' * 60}{C_RESET}")
    print(f" {C_GREEN}● Kept sentences:{C_RESET}    {len(kept):>3}  →  saved to {C_BOLD}{args.out}{C_RESET}")
    print(f" {C_RED}● Deleted sentences:{C_RESET} {len(deleted):>3}  →  saved to {C_BOLD}{args.del_out}{C_RESET}")
    print(f"{'=' * 60}\n")

    # In-place file removal handling
    if deleted:
        do_in_place = args.in_place
        if not do_in_place and supports_raw_terminal():
            try:
                ans = input(f"{C_YELLOW}Would you also like to remove the {len(deleted)} deleted sentence(s) from the source markdown/text files? [y/N]: {C_RESET}")
                if ans.strip().lower() in ('y', 'yes'):
                    do_in_place = True
            except (KeyboardInterrupt, EOFError):
                pass

        if do_in_place:
            print(f"\n{C_CYAN}Removing deleted sentences from source files (.bak backups created)...{C_RESET}")
            modified = remove_deleted_from_files(deleted)
            if modified:
                for fpath, count in modified:
                    print(f"  {C_GREEN}✓{C_RESET} {fpath} (removed {count} occurrence(s))")
            else:
                print("  No changes made to source files.")

    print(f"{C_GREEN}Done!{C_RESET}\n")


if __name__ == '__main__':
    main()
