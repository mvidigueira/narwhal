# Copyright(C) Facebook, Inc. and its affiliates.
from collections import OrderedDict
import subprocess

from benchmark.config import Committee, Key
from benchmark.utils import Print, PathMaker
from benchmark.commands import CommandMaker

bench_params = {
    'workers': 1,
    'collocate': True,
}

node_params = {
    'header_size': 50,  # bytes
    'max_header_delay': 5_000,  # ms
    'gc_depth': 50,  # rounds
    'sync_retry_delay': 10_000,  # ms
    'sync_retry_nodes': 3,  # number of nodes
    'batch_size': 500_000,  # bytes
    'max_batch_delay': 200  # ms
}

def basic_config(hosts):
        Print.info('Generating configuration files...')

        # Cleanup all local configuration files.
        cmd = CommandMaker.cleanup()
        subprocess.run([cmd], shell=True, stderr=subprocess.DEVNULL)

        # Recompile the latest code.
        cmd = CommandMaker.compile().split()
        subprocess.run(cmd, check=True, cwd=PathMaker.node_crate_path())

        # Create alias for the client and nodes binary.
        cmd = CommandMaker.alias_binaries(PathMaker.binary_path())
        subprocess.run([cmd], shell=True)

        # Generate configuration files.
        keys = []
        key_files = [PathMaker.key_file(i) for i in range(len(hosts))]
        for filename in key_files:
            cmd = CommandMaker.generate_key(filename).split()
            subprocess.run(cmd, check=True)
            keys += [Key.from_file(filename)]

        names = [x.name for x in keys]

        if bench_params.collocate:
            workers = bench_params.workers
            addresses = OrderedDict(
                (x, [y] * (workers + 1)) for x, y in zip(names, hosts)
            )
        else:
            addresses = OrderedDict(
                (x, y) for x, y in zip(names, hosts)
            )
            
        committee = Committee(addresses, 3000)
        committee.print(PathMaker.committee_file())

        node_params.print(PathMaker.parameters_file())

        # Cleanup all nodes and upload configuration files.
        # silk run CommandMaker.cleanup()
        # silk send committee_file
        # silk send key_file*
        # silk send parameters_file

hosts_file = open("hosts.txt", "r")
hosts = hosts_file.readlines()
basic_config(hosts)