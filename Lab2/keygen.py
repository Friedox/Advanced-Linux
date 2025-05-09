#!/usr/bin/env python3
"""
Keygen for Lab2 - Generates license key based on hardware ID
"""
import hashlib
import sys


def generate_license_key(hwid):
    md5_hash = hashlib.md5(hwid.encode()).hexdigest()

    reversed_hash = ""
    for i in range(16):
        byte = md5_hash[i * 2:i * 2 + 2]
        reversed_hash = byte + reversed_hash

    return reversed_hash


def main():
    if len(sys.argv) > 1:
        hwid = sys.argv[1]
    else:
        hwid = "010F8600FFFB8B17"

    license_key = generate_license_key(hwid)

    print(f"Hardware ID: {hwid}")
    print(f"License Key: {license_key}")
    print(f"\nTo set the license attribute:")
    print(f"setfattr -n user.license -v {license_key} ./hack_app")


if __name__ == "__main__":
    main()