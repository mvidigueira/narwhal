# Copyright(C) Facebook, Inc. and its affiliates.
from collections import OrderedDict
import subprocess

from benchmark.config import Committee, Key, NodeParameters, BenchParameters, ConfigError
from benchmark.utils import BenchError, Print, PathMaker
from benchmark.commands import CommandMaker

bench_params = {
    'faults': 0,
    'nodes': [4],
    'workers': 1,
    'collocate': True,
    'rate': [10_000],
    'tx_size': 8,
    'duration': 120,
    'runs': 1,
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

def basic_config(hosts, bench_parameters_dict, node_parameters_dict):
        Print.info('Generating configuration files...')

        try:
            bench_parameters = BenchParameters(bench_parameters_dict)
            node_parameters = NodeParameters(node_parameters_dict)
        except ConfigError as e:
            raise BenchError('Invalid nodes or bench parameters', e)

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

        if bench_parameters.collocate:
            workers = bench_parameters.workers
            addresses = OrderedDict(
                (x, [y] * (workers + 1)) for x, y in zip(names, hosts)
            )
        else:
            addresses = OrderedDict(
                (x, y) for x, y in zip(names, hosts)
            )
            
        committee = Committee(addresses, 3000)
        committee.print(PathMaker.committee_file())

        node_parameters.print(PathMaker.parameters_file())

        # Cleanup all nodes and upload configuration files.
        # silk run CommandMaker.cleanup()
        # silk send committee_file
        # silk send key_file*
        # silk send parameters_file

hosts_file = open("hosts.txt", "r")
hosts = hosts_file.readlines()
basic_config(hosts, bench_params, node_params)