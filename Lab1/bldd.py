#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import re
from collections import defaultdict
import datetime
import logging

ARCH_X86 = "i386 (x86)"
ARCH_X86_64 = "x86-64"
ARCH_ARMV7 = "armv7"
ARCH_AARCH64 = "aarch64"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bldd")


def get_elf_architecture(file_path, verbose=False):
    try:
        if os.path.islink(file_path):
            if verbose:
                logger.debug(f"File {file_path} is a symbolic link, skipping")
            return None
            
        try:
            with open(file_path, 'rb') as f:
                header = f.read(20)
                if header.startswith(b'#!'):
                    if verbose:
                        logger.debug(f"File {file_path} is a script, skipping")
                    return None
        except:
            pass
            
        result = subprocess.run(
            ["readelf", "-h", file_path],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            return None

        output = result.stdout
        
        if verbose:
            logger.debug(f"readelf output for {file_path}:\n{output}")

        if "Machine:" not in output:
            return None

        machine_line = None
        class_line = None
        
        for line in output.splitlines():
            if "Machine:" in line:
                machine_line = line.strip()
            if "Class:" in line:
                class_line = line.strip()
        
        if not machine_line:
            return None
        
        if "Advanced Micro Devices X86-64" in machine_line:
            return ARCH_X86_64
        elif "Intel 80386" in machine_line:
            return ARCH_X86
        elif "AArch64" in machine_line:
            return ARCH_AARCH64
        elif "ARM" in machine_line:
            if class_line and "ELF64" in class_line:
                return ARCH_AARCH64
            else:
                return ARCH_ARMV7
                
        return None
    except Exception as e:
        logger.debug(f"Error determining architecture for {file_path}: {e}")
        return None


def is_executable(file_path):
    if not os.path.isfile(file_path):
        return False

    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'\x7fELF':
                return False

        if os.access(file_path, os.X_OK):
            return True

        result = subprocess.run(
            ["file", "-b", file_path],
            capture_output=True,
            text=True,
            check=False
        )

        return "executable" in result.stdout.lower()
    except Exception as e:
        logger.debug(f"Error checking if {file_path} is executable: {e}")
        return False


def get_shared_libraries(file_path, use_tool="objdump"):
    try:
        if use_tool == "objdump":
            cmd = ["objdump", "-x", file_path]
            pattern = r'NEEDED\s+(.+)$'
        elif use_tool == "readelf":
            cmd = ["readelf", "-d", file_path]
            pattern = r'\(NEEDED\)[^[]*\[([^]]+)\]'
        else:
            raise ValueError(f"Unsupported tool: {use_tool}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            return []

        needed_libs = []
        for line in result.stdout.splitlines():
            match = re.search(pattern, line.strip())
            if match:
                needed_libs.append(match.group(1).strip())

        return needed_libs
    except Exception as e:
        logger.debug(f"Error getting dependencies for {file_path} using {use_tool}: {e}")
        return []


def scan_directory(directory, libraries=None, verbose=False, tool="objdump"):
    results = defaultdict(lambda: defaultdict(list))
    scanned_files = 0
    matching_files = 0

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)

            scanned_files += 1
            if verbose and scanned_files % 100 == 0:
                logger.info(f"Scanned {scanned_files} files...")

            if not is_executable(file_path):
                continue

            arch = get_elf_architecture(file_path, verbose)
            if not arch:
                continue

            deps = get_shared_libraries(file_path, tool)

            if libraries:
                matching_deps = []
                for dep in deps:
                    if any(requested.lower() in dep.lower() for requested in libraries):
                        matching_deps.append(dep)
                deps = matching_deps

            if deps:
                matching_files += 1
                for dep in deps:
                    results[arch][dep].append(file_path)

    if verbose:
        logger.info(
            f"Scanning completed. Scanned {scanned_files} files, found {matching_files} matching executables.")

    return results


def generate_text_report(results, directory, output_path):
    with open(output_path, 'w') as f:
        f.write(f"Report on dynamic used libraries by ELF executables on {os.path.abspath(directory)}\n")
        f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for arch in sorted(results.keys()):
            f.write(f"{'-' * 10} {arch} {'-' * 10}\n")

            sorted_libs = sorted(
                results[arch].items(),
                key=lambda x: len(x[1]),
                reverse=True
            )

            for lib, execs in sorted_libs:
                f.write(f"{lib} ({len(execs)} execs)\n")
                for exe in execs:
                    f.write(f"-> {exe}\n")

            f.write("\n")

    return output_path


def generate_pdf_report(results, directory, output_path):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        logger.error("reportlab is not installed. Please install it: pip install reportlab")
        return None

    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Report on dynamic used libraries by ELF executables", styles['Title']))
    elements.append(Paragraph(f"Scanned directory: {os.path.abspath(directory)}", styles['Normal']))
    elements.append(
        Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    for arch in sorted(results.keys()):
        elements.append(Paragraph(f"{arch}", styles['Heading1']))
        elements.append(Spacer(1, 6))

        sorted_libs = sorted(
            results[arch].items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        for lib, execs in sorted_libs:
            elements.append(Paragraph(f"{lib} ({len(execs)} execs)", styles['Heading2']))

            data = [[exe] for exe in execs]
            if data:
                table = Table(data)
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Courier'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ]))
                elements.append(table)

            elements.append(Spacer(1, 12))

    doc.build(elements)
    return output_path


def main():
    banner = """
██████╗ ██╗     ██████╗ ██████╗ 
██╔══██╗██║     ██╔══██╗██╔══██╗
██████╔╝██║     ██║  ██║██║  ██║
██╔══██╗██║     ██║  ██║██║  ██║
██████╔╝███████╗██████╔╝██████╔╝
╚═════╝ ╚══════╝╚═════╝ ╚═════╝ 
                                
Backward LDD - Find executables using specified libraries
"""
    parser = argparse.ArgumentParser(
        description="bldd (backward ldd) - Shows all executable files using specified shared libraries.",
        epilog="""
Examples:
  bldd.py -d /usr/bin -l libc.so.6 -o report.txt
    Scans /usr/bin for executables using libc.so.6 and saves to report.txt

  bldd.py -d /usr/bin -l libc.so.6 libm.so.6 -f pdf -o report.pdf
    Scans /usr/bin for executables using libc.so.6 or libm.so.6 and saves as PDF

  bldd.py -d /usr/bin -v
    Scans /usr/bin for all shared libraries with verbose output

  bldd.py -d /usr/bin -t readelf
    Scans /usr/bin using readelf instead of objdump
        """
    )
    
    print(banner)

    parser.add_argument(
        "-d", "--directory",
        default=".",
        help="Directory to scan for executables (default: current directory)"
    )

    parser.add_argument(
        "-l", "--libraries",
        nargs="+",
        help="Specific libraries to search for (e.g., libc.so.6)"
    )

    parser.add_argument(
        "-o", "--output",
        default="bldd_report",
        help="Output file path (default: bldd_report.[txt|pdf])"
    )

    parser.add_argument(
        "-f", "--format",
        choices=["txt", "pdf"],
        default="txt",
        help="Report format (default: txt)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "-t", "--tool",
        choices=["objdump", "readelf"],
        default="objdump",
        help="Tool for extracting dependencies (default: objdump)"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if not os.path.isdir(args.directory):
        logger.error(f"Error: Directory '{args.directory}' does not exist")
        return 1

    for tool in [args.tool, "readelf"]:
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=False)
        except FileNotFoundError:
            logger.error(f"Error: {tool} is not installed. Please install it first.")
            return 1

    output_file = args.output
    if not output_file.endswith(f".{args.format}"):
        output_file = f"{output_file}.{args.format}"

    logger.info(f"Scanning directory: {args.directory}")
    results = scan_directory(
        args.directory,
        libraries=args.libraries,
        verbose=args.verbose,
        tool=args.tool
    )

    if not results:
        logger.info("No executables found with matching dependencies.")
        return 0

    if args.format == "txt":
        report_path = generate_text_report(results, args.directory, output_file)
        if report_path:
            logger.info(f"Text report generated: {report_path}")
    elif args.format == "pdf":
        report_path = generate_pdf_report(results, args.directory, output_file)
        if report_path:
            logger.info(f"PDF report generated: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())