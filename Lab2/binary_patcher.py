import os
import sys
import subprocess


def find_license_check_cmp(binary_path):
    pattern = b"\x83\x7d\xe4\x00"

    try:
        with open(binary_path, 'rb') as f:
            binary_data = f.read()

        pos = binary_data.find(pattern)
        if pos == -1:
            print("Could not find license comparison instruction")
            return None

        print(f"Found CMP instruction at offset: 0x{pos:x}")
        return pos
    except Exception as e:
        print(f"Error reading binary file: {e}")
        return None


def patch_binary(binary_path, output_path):
    cmp_offset = find_license_check_cmp(binary_path)
    if cmp_offset is None:
        return False

    try:
        with open(binary_path, 'rb') as f:
            binary_data = bytearray(f.read())

        original_bytes = binary_data[cmp_offset:cmp_offset + 4]
        print(f"Original bytes: {original_bytes.hex(' ')}")

        binary_data[cmp_offset + 3] = 0x01

        with open(output_path, 'wb') as f:
            f.write(binary_data)

        os.chmod(output_path, 0o755)

        print(f"Patch applied. New bytes: {binary_data[cmp_offset:cmp_offset + 4].hex(' ')}")
        print(f"Patched file saved as: {output_path}")

        return True
    except Exception as e:
        print(f"Error patching binary file: {e}")
        return False


def create_bsdiff_patch(original_path, patched_path, patch_path):
    try:
        subprocess.run(["bsdiff", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("bsdiff utility not found. Install it with:")
        print("  sudo apt-get install bsdiff")
        return False

    try:
        subprocess.run(["bsdiff", original_path, patched_path, patch_path], check=True)
        print(f"Created bsdiff patch: {patch_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating bsdiff patch: {e}")
        return False


def apply_bsdiff_patch(original_path, output_path, patch_path):
    try:
        subprocess.run(["bspatch", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("bspatch utility not found. Install it with:")
        print("  sudo apt-get install bsdiff")
        return False

    try:
        subprocess.run(["bspatch", original_path, output_path, patch_path], check=True)
        print(f"Patch applied. Result: {output_path}")

        os.chmod(output_path, 0o755)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error applying bspatch: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} patch /path/to/original/binary/file [/path/to/output]")
        print(f"  {sys.argv[0]} create-patch /path/to/original/file /path/to/patched/file [/path/to/patch]")
        print(f"  {sys.argv[0]} apply-patch /path/to/original/file /path/to/patch [/path/to/output]")
        return

    command = sys.argv[1]

    if command == "patch":
        if len(sys.argv) < 3:
            print("No path to source file specified")
            return

        original_path = sys.argv[2]

        if len(sys.argv) >= 4:
            output_path = sys.argv[3]
        else:
            output_path = original_path + ".patched"

        if not os.path.exists(original_path):
            print(f"File not found: {original_path}")
            return

        success = patch_binary(original_path, output_path)
        if success:
            print("Patching completed successfully")

    elif command == "create-patch":
        if len(sys.argv) < 4:
            print("Paths to original and patched files not specified")
            return

        original_path = sys.argv[2]
        patched_path = sys.argv[3]

        if len(sys.argv) >= 5:
            patch_path = sys.argv[4]
        else:
            patch_path = "binary.patch"

        if not os.path.exists(original_path) or not os.path.exists(patched_path):
            print("One of the specified files does not exist")
            return

        create_bsdiff_patch(original_path, patched_path, patch_path)

    elif command == "apply-patch":
        if len(sys.argv) < 4:
            print("Paths to original file and patch not specified")
            return

        original_path = sys.argv[2]
        patch_path = sys.argv[3]

        if len(sys.argv) >= 5:
            output_path = sys.argv[4]
        else:
            output_path = original_path + ".patched"

        if not os.path.exists(original_path) or not os.path.exists(patch_path):
            print("One of the specified files does not exist")
            return

        apply_bsdiff_patch(original_path, output_path, patch_path)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()