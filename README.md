# INFO: task hung in f2fs_write_data_pages (fs/f2fs/data.c:3834, v7.4-rc3)

Syzkaller-found F2FS writeback hang on Linux v7.4-rc3, reproduced and verified
by the KernSight state-primed pipeline using `snapshot_restore`.

## Summary

The report shows an F2FS writeback path blocked for more than 140 seconds in
`__f2fs_write_data_pages()` while waiting for the `sbi->writepages` mutex:

```text
INFO: task syz.2.19:29337 blocked for more than 142 seconds.
task:syz.2.19 state:D
Call Trace:
 __schedule
 schedule_preempt_disabled
 __mutex_lock
 __f2fs_write_data_pages fs/f2fs/data.c:3834 [inline]
 f2fs_write_data_pages+0xfaf/0x14a0 fs/f2fs/data.c:3879
 do_writepages
 filemap_writeback
 file_write_and_wait_range
 f2fs_do_sync_file
 f2fs_sync_file
 vfs_fsync_range
 f2fs_file_write_iter
 do_pwritev
 __x64_sys_pwritev
```

The source at the blocking point is:

```c
if (__should_serialize_io(inode, wbc)) {
    mutex_lock(&sbi->writepages);
    locked = true;
}
```

A second task in the same report is blocked in `f2fs_fallocate()`:

```text
INFO: task syz.2.19:29526 blocked for more than 142 seconds.
rwsem_down_write_slowpath
inode_lock
f2fs_fallocate+0x347/0x3ca0 fs/f2fs/file.c:2116
vfs_fallocate
__x64_sys_fallocate
```

The lock dump also shows a task holding `sbi->writepages` together with
`sbi->gc_lock`, `fi->i_gc_rwsem[0..1]`, and `sbi->cp_rwsem`. This suggests a
writeback / garbage-collection / fallocate lock dependency, but the root cause
is not confirmed here.

## Verification

- Pipeline attempts 1, 3, 4: budget exhausted
- Pipeline attempt 2: triggered but unverified
- Pipeline attempt 5: `confirmed=true`, `status=verified`
- Time: `2026-11-19T08:05:41Z`
- Verification scope: **snapshot_restore**
- 140 replay programs, 0 priming programs
- The pipeline exported a 2.5 GiB pre-crash state snapshot and verified the
  testcase from that frozen state
- Independent external fresh-VM verification: **3/3**
  - run 1 hit after 205 s
  - run 2 hit after 206 s
  - run 3 hit after 206 s
- Evidence: `reproducer/repro.outcomes.jsonl`, `reproducer/repro.stats`,
  `reproducer/repro.report`, `reproducer/repro.context.json`,
  `external-verify/`

## How to reproduce

Environment: Debian trixie x86_64 guest (6 GiB RAM, 4 vCPU, KVM), kernel built
from v7.4-rc3 with CONFIG_KASAN=y, CONFIG_PROVE_LOCKING=y,
CONFIG_F2FS_FS=y, booted with `oops=panic` and `panic_on_warn=1`. See
`environment.txt` and `kernel.config`.

`repro.kernsight.prog` is the complete 141-entry state-reconstruction recipe
(140 replay programs followed by the testcase). It reproduced on three
independent fresh VMs; no state snapshot is required for reproduction:

```sh
# in the guest, as root:
syz-execprog -procs=8 -threaded -repeat=0 \
    -executor ./syz-executor reproducer/repro.kernsight.prog
```

`-repeat=0` repeats until the hung-task report appears. The three external
runs hit after 205-206 seconds.

## Files

- `description`, `environment.txt`, `kernel.config`
- `reproducer/repro.kernsight.prog` — 141-entry state recipe
- `reproducer/repro.priming.prog`, `reproducer/repro.prog`
- `reproducer/repro.report`, `repro.stats`, `repro.outcomes.jsonl`,
  `repro.context.json`, `repro.achieved_state.json`
- `logs/log-0.txt`, `logs/report-0.txt`, `logs/machineInfo-0.txt`,
  `logs/title-stat.json`, `logs/repro-report.txt`, `logs/repro-stats.txt`
- `external-verify/` — three independent fresh-VM serial logs and timings

## Notes

- Crash title: `INFO: task hung in f2fs_write_data_pages`
- Subsystem: F2FS writeback / GC / fallocate locking
- The primary blocked lock is `sbi->writepages`
- This archive records the observed hang and verified reproducer; it does not
  propose a fix
