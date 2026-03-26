#!/usr/bin/env python3
"""Find likely WebREPL hosts (port 8266) on the current /24 network."""

from __future__ import annotations

import argparse
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("1.1.1.1", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


def is_port_open(ip: str, port: int, timeout: float) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((ip, port)) == 0
    except Exception:
        return False
    finally:
        sock.close()


def scan_webrepl_hosts(local_ip: str, timeout: float) -> list[str]:
    octets = local_ip.split(".")
    if len(octets) != 4:
        return []

    prefix = ".".join(octets[:3])
    last_octet = int(octets[3])

    targets = [f"{prefix}.{i}" for i in range(1, 255) if i != last_octet]
    open_hosts: list[str] = []

    with ThreadPoolExecutor(max_workers=64) as pool:
        futures = {pool.submit(is_port_open, ip, 8266, timeout): ip for ip in targets}
        for fut in as_completed(futures):
            ip = futures[fut]
            try:
                if fut.result():
                    open_hosts.append(ip)
            except Exception:
                pass

    open_hosts.sort(key=lambda x: tuple(int(p) for p in x.split(".")))
    return open_hosts


def local_subnet(local_ip: str) -> str:
    octets = local_ip.split(".")
    if len(octets) != 4:
        return "unknown"
    return ".".join(octets[:3]) + ".0/24"


def main() -> int:
    parser = argparse.ArgumentParser(description="Find WebREPL host on local network")
    parser.add_argument("--first", action="store_true", help="Print only the first host found")
    parser.add_argument("--timeout", type=float, default=0.2, help="Per-host TCP timeout in seconds")
    parser.add_argument("--local-ip", action="store_true", help="Print only local IPv4 and exit")
    parser.add_argument("--print-network", action="store_true", help="Print local IP and subnet to stderr")
    args = parser.parse_args()

    local_ip = get_local_ip()

    if args.local_ip:
        print(local_ip)
        return 0

    if args.print_network:
        print(f"[local] ip={local_ip} subnet={local_subnet(local_ip)}", file=sys.stderr)

    hosts = scan_webrepl_hosts(local_ip, args.timeout)

    if not hosts:
        return 1

    if args.first:
        print(hosts[0])
    else:
        for host in hosts:
            print(host)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
