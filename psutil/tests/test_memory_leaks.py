#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Tests for detecting function memory leaks (typically the ones
implemented in C). It does so by calling a function many times and
checking whether process memory usage keeps increasing between
calls or over time.
Note that this may produce false positives (especially on Windows
for some reason).
PyPy appears to be completely unstable for this framework, probably
because of how its JIT handles memory, so tests are skipped.
"""

from __future__ import print_function
import functools
import os

import psutil
import psutil._common
from psutil import FREEBSD
from psutil import LINUX
from psutil import MACOS
from psutil import OPENBSD
from psutil import POSIX
from psutil import SUNOS
from psutil import WINDOWS
from psutil._compat import ProcessLookupError
from psutil._compat import super
from psutil.tests import CIRRUS
from psutil.tests import create_sockets
from psutil.tests import get_test_subprocess
from psutil.tests import get_testfn
from psutil.tests import HAS_CPU_AFFINITY
from psutil.tests import HAS_CPU_FREQ
from psutil.tests import HAS_ENVIRON
from psutil.tests import HAS_IONICE
from psutil.tests import HAS_MEMORY_MAPS
from psutil.tests import HAS_NET_IO_COUNTERS
from psutil.tests import HAS_PROC_CPU_NUM
from psutil.tests import HAS_PROC_IO_COUNTERS
from psutil.tests import HAS_RLIMIT
from psutil.tests import HAS_SENSORS_BATTERY
from psutil.tests import HAS_SENSORS_FANS
from psutil.tests import HAS_SENSORS_TEMPERATURES
from psutil.tests import reap_children
from psutil.tests import skip_on_access_denied
from psutil.tests import TestMemoryLeak
from psutil.tests import TRAVIS
from psutil.tests import unittest

SKIP_PYTHON_IMPL = True
cext = psutil._psplatform.cext
thisproc = psutil.Process()


# ===================================================================
# utils
# ===================================================================


def skip_if_linux():
    return unittest.skipIf(LINUX and SKIP_PYTHON_IMPL,
                           "worthless on LINUX (pure python)")


# ===================================================================
# Process class
# ===================================================================


class TestProcessObjectLeaks(TestMemoryLeak):
    """Test leaks of Process class methods."""

    proc = thisproc

    def test_coverage(self):
        skip = set((
            "pid", "as_dict", "children", "cpu_affinity", "cpu_percent",
            "ionice", "is_running", "kill", "memory_info_ex", "memory_percent",
            "nice", "oneshot", "parent", "parents", "rlimit", "send_signal",
            "suspend", "terminate", "wait"))
        for name in dir(psutil.Process):
            if name.startswith('_'):
                continue
            if name in skip:
                continue
            self.assertTrue(hasattr(self, "test_" + name), msg=name)

    @skip_if_linux()
    def test_name(self):
        self.execute(self.proc.name)

    @skip_if_linux()
    def test_cmdline(self):
        self.execute(self.proc.cmdline)

    @skip_if_linux()
    def test_exe(self):
        self.execute(self.proc.exe)

    @skip_if_linux()
    def test_ppid(self):
        self.execute(self.proc.ppid)

    @unittest.skipIf(not POSIX, "POSIX only")
    @skip_if_linux()
    def test_uids(self):
        self.execute(self.proc.uids)

    @unittest.skipIf(not POSIX, "POSIX only")
    @skip_if_linux()
    def test_gids(self):
        self.execute(self.proc.gids)

    @skip_if_linux()
    def test_status(self):
        self.execute(self.proc.status)

    def test_nice_get(self):
        self.execute(self.proc.nice)

    def test_nice_set(self):
        niceness = thisproc.nice()
        self.execute(lambda: self.proc.nice(niceness))

    @unittest.skipIf(not HAS_IONICE, "not supported")
    def test_ionice_get(self):
        self.execute(self.proc.ionice)

    @unittest.skipIf(not HAS_IONICE, "not supported")
    def test_ionice_set(self):
        if WINDOWS:
            value = thisproc.ionice()
            self.execute(lambda: self.proc.ionice(value))
        else:
            self.execute(lambda: self.proc.ionice(psutil.IOPRIO_CLASS_NONE))
            fun = functools.partial(cext.proc_ioprio_set, os.getpid(), -1, 0)
            self.execute_w_exc(OSError, fun)

    @unittest.skipIf(not HAS_PROC_IO_COUNTERS, "not supported")
    @skip_if_linux()
    def test_io_counters(self):
        self.execute(self.proc.io_counters)

    @unittest.skipIf(POSIX, "worthless on POSIX")
    def test_username(self):
        self.execute(self.proc.username)

    @skip_if_linux()
    def test_create_time(self):
        self.execute(self.proc.create_time)

    @skip_if_linux()
    @skip_on_access_denied(only_if=OPENBSD)
    def test_num_threads(self):
        self.execute(self.proc.num_threads)

    @unittest.skipIf(not WINDOWS, "WINDOWS only")
    def test_num_handles(self):
        self.execute(self.proc.num_handles)

    @unittest.skipIf(not POSIX, "POSIX only")
    @skip_if_linux()
    def test_num_fds(self):
        self.execute(self.proc.num_fds)

    @skip_if_linux()
    def test_num_ctx_switches(self):
        self.execute(self.proc.num_ctx_switches)

    @skip_if_linux()
    @skip_on_access_denied(only_if=OPENBSD)
    def test_threads(self):
        self.execute(self.proc.threads)

    @skip_if_linux()
    def test_cpu_times(self):
        self.execute(self.proc.cpu_times)

    @skip_if_linux()
    @unittest.skipIf(not HAS_PROC_CPU_NUM, "not supported")
    def test_cpu_num(self):
        self.execute(self.proc.cpu_num)

    @skip_if_linux()
    def test_memory_info(self):
        self.execute(self.proc.memory_info)

    @skip_if_linux()
    def test_memory_full_info(self):
        self.execute(self.proc.memory_full_info)

    @unittest.skipIf(not POSIX, "POSIX only")
    @skip_if_linux()
    def test_terminal(self):
        self.execute(self.proc.terminal)

    @unittest.skipIf(POSIX and SKIP_PYTHON_IMPL,
                     "worthless on POSIX (pure python)")
    def test_resume(self):
        self.execute(self.proc.resume)

    @skip_if_linux()
    def test_cwd(self):
        self.execute(self.proc.cwd)

    @unittest.skipIf(not HAS_CPU_AFFINITY, "not supported")
    def test_cpu_affinity_get(self):
        self.execute(self.proc.cpu_affinity)

    @unittest.skipIf(not HAS_CPU_AFFINITY, "not supported")
    def test_cpu_affinity_set(self):
        affinity = thisproc.cpu_affinity()
        self.execute(lambda: self.proc.cpu_affinity(affinity))
        if not TRAVIS:
            self.execute_w_exc(
                ValueError, lambda: self.proc.cpu_affinity([-1]))

    @skip_if_linux()
    def test_open_files(self):
        with open(get_testfn(), 'w'):
            self.execute(self.proc.open_files)

    @unittest.skipIf(not HAS_MEMORY_MAPS, "not supported")
    @skip_if_linux()
    def test_memory_maps(self):
        self.execute(self.proc.memory_maps)

    @unittest.skipIf(not LINUX, "LINUX only")
    @unittest.skipIf(not HAS_RLIMIT, "not supported")
    def test_rlimit_get(self):
        self.execute(lambda: self.proc.rlimit(psutil.RLIMIT_NOFILE))

    @unittest.skipIf(not LINUX, "LINUX only")
    @unittest.skipIf(not HAS_RLIMIT, "not supported")
    def test_rlimit_set(self):
        limit = thisproc.rlimit(psutil.RLIMIT_NOFILE)
        self.execute(lambda: self.proc.rlimit(psutil.RLIMIT_NOFILE, limit))
        self.execute_w_exc(OSError, lambda: self.proc.rlimit(-1))

    @skip_if_linux()
    # Windows implementation is based on a single system-wide
    # function (tested later).
    @unittest.skipIf(WINDOWS, "worthless on WINDOWS")
    def test_connections(self):
        # TODO: UNIX sockets are temporarily implemented by parsing
        # 'pfiles' cmd  output; we don't want that part of the code to
        # be executed.
        with create_sockets():
            kind = 'inet' if SUNOS else 'all'
            self.execute(lambda: self.proc.connections(kind))

    @unittest.skipIf(not HAS_ENVIRON, "not supported")
    def test_environ(self):
        self.execute(self.proc.environ)

    @unittest.skipIf(not WINDOWS, "WINDOWS only")
    def test_proc_info(self):
        self.execute(cext.proc_info, os.getpid())


@unittest.skipIf(not WINDOWS, "WINDOWS only")
class TestProcessDualImplementation(TestMemoryLeak):

    def test_cmdline_peb_true(self):
        self.execute(lambda: cext.proc_cmdline(os.getpid(), use_peb=True))

    def test_cmdline_peb_false(self):
        self.execute(lambda: cext.proc_cmdline(os.getpid(), use_peb=False))


class TestTerminatedProcessLeaks(TestProcessObjectLeaks):
    """Repeat the tests above looking for leaks occurring when dealing
    with terminated processes raising NoSuchProcess exception.
    The C functions are still invoked but will follow different code
    paths. We'll check those code paths.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        p = get_test_subprocess()
        cls.proc = psutil.Process(p.pid)
        cls.proc.kill()
        cls.proc.wait()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        reap_children()

    def _call(self, fun):
        try:
            fun()
        except psutil.NoSuchProcess:
            pass

    if WINDOWS:

        def test_kill(self):
            self.execute(self.proc.kill)

        def test_terminate(self):
            self.execute(self.proc.terminate)

        def test_suspend(self):
            self.execute(self.proc.suspend)

        def test_resume(self):
            self.execute(self.proc.resume)

        def test_wait(self):
            self.execute(self.proc.wait)

        def test_proc_info(self):
            # test dual implementation
            def call():
                try:
                    return cext.proc_info(self.proc.pid)
                except ProcessLookupError:
                    pass

            self.execute(call)


# ===================================================================
# system APIs
# ===================================================================


class TestModuleFunctionsLeaks(TestMemoryLeak):
    """Test leaks of psutil module functions."""

    def test_coverage(self):
        skip = set((
            "version_info", "__version__", "process_iter", "wait_procs",
            "cpu_percent", "cpu_times_percent", "cpu_count"))
        for name in psutil.__all__:
            if not name.islower():
                continue
            if name in skip:
                continue
            self.assertTrue(hasattr(self, "test_" + name), msg=name)

    # --- cpu

    @skip_if_linux()
    def test_cpu_count_logical(self):
        self.execute(lambda: psutil.cpu_count(logical=True))

    @skip_if_linux()
    def test_cpu_count_physical(self):
        self.execute(lambda: psutil.cpu_count(logical=False))

    @skip_if_linux()
    def test_cpu_times(self):
        self.execute(psutil.cpu_times)

    @skip_if_linux()
    def test_per_cpu_times(self):
        self.execute(lambda: psutil.cpu_times(percpu=True))

    @skip_if_linux()
    def test_cpu_stats(self):
        self.execute(psutil.cpu_stats)

    @skip_if_linux()
    @unittest.skipIf(not HAS_CPU_FREQ, "not supported")
    def test_cpu_freq(self):
        self.execute(psutil.cpu_freq)

    @unittest.skipIf(not WINDOWS, "WINDOWS only")
    def test_getloadavg(self):
        self.execute(psutil.getloadavg)

    # --- mem

    def test_virtual_memory(self):
        self.execute(psutil.virtual_memory)

    # TODO: remove this skip when this gets fixed
    @unittest.skipIf(SUNOS, "worthless on SUNOS (uses a subprocess)")
    def test_swap_memory(self):
        self.execute(psutil.swap_memory)

    @unittest.skipIf(POSIX and SKIP_PYTHON_IMPL,
                     "worthless on POSIX (pure python)")
    def test_pid_exists(self):
        self.execute(lambda: psutil.pid_exists(os.getpid()))

    # --- disk

    @unittest.skipIf(POSIX and SKIP_PYTHON_IMPL,
                     "worthless on POSIX (pure python)")
    def test_disk_usage(self):
        self.execute(lambda: psutil.disk_usage('.'))

    def test_disk_partitions(self):
        self.execute(psutil.disk_partitions)

    @unittest.skipIf(LINUX and not os.path.exists('/proc/diskstats'),
                     '/proc/diskstats not available on this Linux version')
    @skip_if_linux()
    def test_disk_io_counters(self):
        self.execute(lambda: psutil.disk_io_counters(nowrap=False))

    # --- proc

    @skip_if_linux()
    def test_pids(self):
        self.execute(psutil.pids)

    # --- net

    @unittest.skipIf(TRAVIS and MACOS, "false positive on TRAVIS + MACOS")
    @unittest.skipIf(CIRRUS and FREEBSD, "false positive on CIRRUS + FREEBSD")
    @skip_if_linux()
    @unittest.skipIf(not HAS_NET_IO_COUNTERS, 'not supported')
    def test_net_io_counters(self):
        self.execute(lambda: psutil.net_io_counters(nowrap=False))

    @skip_if_linux()
    @unittest.skipIf(MACOS and os.getuid() != 0, "need root access")
    def test_net_connections(self):
        with create_sockets():
            self.execute(psutil.net_connections)

    def test_net_if_addrs(self):
        # Note: verified that on Windows this was a false positive.
        self.execute(psutil.net_if_addrs,
                     tolerance=80 * 1024 if WINDOWS else 4096)

    @unittest.skipIf(TRAVIS, "EPERM on travis")
    def test_net_if_stats(self):
        self.execute(psutil.net_if_stats)

    # --- sensors

    @skip_if_linux()
    @unittest.skipIf(not HAS_SENSORS_BATTERY, "not supported")
    def test_sensors_battery(self):
        self.execute(psutil.sensors_battery)

    @skip_if_linux()
    @unittest.skipIf(not HAS_SENSORS_TEMPERATURES, "not supported")
    def test_sensors_temperatures(self):
        self.execute(psutil.sensors_temperatures)

    @skip_if_linux()
    @unittest.skipIf(not HAS_SENSORS_FANS, "not supported")
    def test_sensors_fans(self):
        self.execute(psutil.sensors_fans)

    # --- others

    @skip_if_linux()
    def test_boot_time(self):
        self.execute(psutil.boot_time)

    @unittest.skipIf(WINDOWS, "XXX produces a false positive on Windows")
    def test_users(self):
        self.execute(psutil.users)

    if WINDOWS:

        # --- win services

        def test_win_service_iter(self):
            self.execute(cext.winservice_enumerate)

        def test_win_service_get(self):
            pass

        def test_win_service_get_config(self):
            name = next(psutil.win_service_iter()).name()
            self.execute(lambda: cext.winservice_query_config(name))

        def test_win_service_get_status(self):
            name = next(psutil.win_service_iter()).name()
            self.execute(lambda: cext.winservice_query_status(name))

        def test_win_service_get_description(self):
            name = next(psutil.win_service_iter()).name()
            self.execute(lambda: cext.winservice_query_descr(name))


if __name__ == '__main__':
    from psutil.tests.runner import run_from_name
    run_from_name(__file__)
