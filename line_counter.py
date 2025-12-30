import os
import argparse
from typing import List, Dict, Any, Set, Optional

# Configuration - customize these for your project
DEFAULT_SKIP_DIRS = {
    '__pycache__', '.git', 'node_modules', '.next',
    'venv', 'env', '.venv', '.env',
    'logs', '!backups', 'tests', 'vendor'
}

DEFAULT_SKIP_EXTENSIONS = {
    # Document files
    '.md', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.odt', '.ods', '.odp', '.rtf', '.txt', '.csv', '.tsv',
    
    # Database files
    '.db', '.sqlite', '.sqlite3', '.db3',  # SQLite
    '.mdb', '.accdb',  # Access
    '.sql',  # SQL dumps
    '.frm', '.myd', '.myi',  # MySQL
    
    # Image files
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.webp', '.svg', '.ico', '.psd', '.ai', '.eps', '.raw',
    '.heic', '.heif', '.indd', '.cr2', '.nef', '.arw', '.dng',
    
    # Archive/compressed files
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    
    # Backup and cache files
    '.bak', '.tmp', '.swp', '.swo', '~',
    
    # Binary/compiled files
    '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.class',
    
    # System files
    '.ini', '.cfg', '.conf', '.log', '.lock'
}

# 🚀 NEW CONFIGURATION: Add a set for specific filenames to skip
DEFAULT_SKIP_FILENAMES = {
    'package-lock.json',
    'yarn.lock',
    'pnpm-lock.yaml',
    'Gemfile.lock',
    'composer.lock',
    'requirements.txt', # You might want to include this or not, depending on your project
    'Pipfile.lock',
    'mix.lock',
    'Cargo.lock',
    'go.sum',
    'checksums.txt',
    '.DS_Store',
    'Thumbs.db'
}

def count_lines(filepath: str) -> int:
    """Count the number of lines in a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        int: Number of lines in the file, or 0 if file can't be read
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except (IOError, UnicodeDecodeError):
        return 0

def get_file_info(
    startpath: str,
    skip_dirs: Optional[Set[str]] = None,
    skip_extensions: Optional[Set[str]] = None,
    skip_filenames: Optional[Set[str]] = None # 🌟 Add new parameter
) -> List[Dict[str, Any]]:
    """Get information about all files in a directory tree.
    
    Args:
        startpath: Root directory to scan
        skip_dirs: Set of directory names to skip
        skip_extensions: Set of file extensions to skip (including leading dot)
        skip_filenames: Set of specific filenames to skip (e.g., 'package-lock.json') # 🌟 Documentation update
        
    Returns:
        List of dictionaries with file information
    """
    if skip_dirs is None:
        skip_dirs = DEFAULT_SKIP_DIRS
    if skip_extensions is None:
        skip_extensions = DEFAULT_SKIP_EXTENSIONS
    if skip_filenames is None: # 🌟 Initialize new parameter
        skip_filenames = DEFAULT_SKIP_FILENAMES
        
    file_info = []
    
    for root, dirs, files in os.walk(startpath, topdown=True):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            # 🐞 Existing skip logic: Skip hidden files, __init__.py, and desktop.ini
            if file.startswith('.') or file == 'desktop.ini' or file == '__init__.py':
                continue
            
            # 🚀 NEW SKIP LOGIC: Skip specific filenames
            if file in skip_filenames:
                continue
                
            # Get file extension
            _, ext = os.path.splitext(file)
            ext = ext.lower()
            
            # Skip files with blacklisted extensions
            if ext in skip_extensions:
                continue
                
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, startpath).replace('\\', '/')
            
            # Skip files we can't access
            try:
                size_kb = os.path.getsize(filepath) / 1024
            except OSError:
                continue
                
            line_count = count_lines(filepath)
            
            file_info.append({
                'path': rel_path,
                'lines': line_count,
                'size_kb': size_kb,
                'ext': ext[1:] if ext else 'none'
            })
    
    return sorted(file_info, key=lambda x: x['path'].lower())

def generate_markdown_table(file_info: List[Dict[str, Any]]) -> str:
    """Generate a markdown table from file information, sorted by line count (descending).
    
    Args:
        file_info: List of file information dictionaries
        
    Returns:
        str: Formatted markdown table
    """
    if not file_info:
        return "*No files found*"
    
    # Sort by line count (descending) then by filename (ascending)
    sorted_info = sorted(
        file_info,
        key=lambda x: (-x['lines'], x['path'].lower())
    )
        
    table = ["| File | Extension | Lines | Size (KB) |", "|------|-----------|-------|-----------|"]
    for info in sorted_info:
        table.append(f"| `{info['path']}` | {info['ext']} | {info['lines']:,} | {info['size_kb']:.1f} |")
    
    return '\n'.join(table)

def generate_file_table(files: List[Dict[str, Any]], show_rank: bool = False) -> str:
    """Generate a markdown table from file information.
    
    Args:
        files: List of file information dictionaries
        show_rank: Whether to show rank column
        
    Returns:
        str: Formatted markdown table
    """
    if not files:
        return "*No files found*"
    
    headers = ["Rank", "File", "Lines", "Size (KB)"] if show_rank else ["File", "Lines", "Size (KB)"]
    separator = ["------"] * len(headers)
    
    table = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(separator) + "|"
    ]
    
    for i, info in enumerate(files, 1):
        if show_rank:
            table.append(f"| {i} | `{info['path']}` | {info['lines']:,} | {info['size_kb']:.1f} |")
        else:
            table.append(f"| `{info['path']}` | {info['lines']:,} | {info['size_kb']:.1f} |")
    
    return '\n'.join(table)

def generate_top_files_table(file_info: List[Dict[str, Any]], top_n: int = 10) -> str:
    """Generate a table of the largest files by line count.
    
    Args:
        file_info: List of file information dictionaries
        top_n: Number of top files to include
        
    Returns:
        str: Formatted markdown table
    """
    if not file_info:
        return "*No files found*"
        
    # Filter out empty files and sort by line count (descending)
    non_empty_files = [f for f in file_info if f['lines'] > 0]
    if not non_empty_files:
        return "*No non-empty files found*"
        
    sorted_files = sorted(non_empty_files, key=lambda x: x['lines'], reverse=True)[:top_n]
    return generate_file_table(sorted_files, show_rank=True)

def generate_bottom_files_table(file_info: List[Dict[str, Any]], bottom_n: int = 5) -> str:
    """Generate a table of the smallest files by line count.
    
    Args:
        file_info: List of file information dictionaries
        bottom_n: Number of bottom files to include
        
    Returns:
        str: Formatted markdown table
    """
    if not file_info:
        return "*No files found*"
        
    # Filter out empty files and sort by line count (ascending)
    non_empty_files = [f for f in file_info if f['lines'] > 0]
    if not non_empty_files:
        return "*No non-empty files found*"
        
    sorted_files = sorted(non_empty_files, key=lambda x: x['lines'])[:bottom_n]
    return generate_file_table(sorted_files, show_rank=True)

def generate_exclusions_list() -> str:
    """Generate a formatted list of excluded file types and directories."""
    categories = {
        "Document Files": ['.md', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                         '.odt', '.ods', '.odp', '.rtf', '.txt', '.csv', '.tsv'],
        "Database Files": ['.db', '.sqlite', '.sqlite3', '.db3', '.mdb', '.accdb', '.sql',
                          '.frm', '.myd', '.myi'],
        "Image Files": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
                       '.webp', '.svg', '.ico', '.psd', '.ai', '.eps', '.raw',
                       '.heic', '.heif', '.indd', '.cr2', '.nef', '.arw', '.dng'],
        "Archive/Compressed Files": ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
        "Backup and Cache Files": ['.bak', '.tmp', '.swp', '.swo', '~'],
        "Binary/Compiled Files": ['.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.class'],
        "System Files": ['.ini', '.cfg', '.conf', '.log', '.lock', '.lnk']  # .lnk = Windows shortcuts
    }
    
    lines = ["## Excluded File Types and Directories\n\n"]
    
    for category, extensions in categories.items():
        lines.append(f"### {category}")
        lines.append(", ".join(f"`{ext}`" for ext in sorted(extensions)))
        lines.append("\n")
    
    lines.append("### Excluded Directories\n")
    lines.append(", ".join(f"`{d}`" for d in sorted(DEFAULT_SKIP_DIRS)))
    lines.append("\n")
    
    # 🚀 Add excluded filenames to the report
    lines.append("### Excluded Specific Filenames\n")
    lines.append(", ".join(f"`{f}`" for f in sorted(DEFAULT_SKIP_FILENAMES)))
    lines.append("\n\n*Note: Also excludes hidden files (starting with '.'), `__init__.py`, `desktop.ini`, and Windows shortcut (`.lnk`) files")
    
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate a line count report for a codebase.')
    parser.add_argument(
        'path', 
        nargs='?', 
        default=os.getcwd(),
        help='Path to analyze (default: current directory)'
    )
    parser.add_argument(
        '-o', '--output',
        default='LINE_COUNT.md',
        help='Output file (default: LINE_COUNT.md)'
    )
    parser.add_argument(
        '-n', '--top-n',
        type=int,
        default=10,
        help='Number of top files to show (default: 10)'
    )
    return parser.parse_args()


def main() -> None:
    """Main function to generate the line count report."""
    args = parse_arguments()
    
    # Normalize the path
    start_path = os.path.abspath(args.path)
    
    if not os.path.isdir(start_path):
        print(f"Error: '{start_path}' is not a valid directory")
        return
    
    print(f"Analyzing files in: {start_path}")
    # 🌟 Pass the new skip_filenames parameter
    file_info = get_file_info(start_path, skip_filenames=DEFAULT_SKIP_FILENAMES) 
    
    if not file_info:
        print("No files found matching the criteria.")
        return
    
    # Generate the report sections
    report = [
        "# Line Count Report\n\n",
        f"*Generated for: {start_path}*\n\n",
        
        "## File Statistics\n\n",
        f"- **Total files analyzed:** {len(file_info):,}\n",
        f"- **Total lines of code:** {sum(f['lines'] for f in file_info):,}\n\n",
        
        "## Largest Files\n\n",
        "*Top 10 files by line count*\n\n",
        generate_top_files_table(file_info, args.top_n),
        "\n\n---\n\n",
        
        "## Smallest Files\n\n",
        "*Top 5 smallest non-empty files*\n\n",
        generate_bottom_files_table(file_info, 5),
        "\n\n---\n\n",
        
        "## Complete File List\n\n",
        "*Sorted by line count (descending), then by filename*\n\n",
        generate_markdown_table(file_info),
        "\n\n---\n\n",
        
        generate_exclusions_list()
    ]
    
    # Write to file
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.writelines(report)
        print(f"Report generated successfully: {os.path.abspath(args.output)}")
    except IOError as e:
        print(f"Error writing to {args.output}: {e}")


if __name__ == "__main__":
    main()