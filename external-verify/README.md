# Independent external verification

Three fresh-VM runs were performed outside the main KernSight pipeline. Each
run used a new qcow2 overlay, the v7.4-rc3 kernel, the standard Debian trixie
guest, and the archived `repro.kernsight.prog`.

Command shape:

```sh
syz-execprog -procs=8 -threaded -repeat=0 \
    -executor ./syz-executor reproducer/repro.kernsight.prog
```

Results:

- Run 1: target hit after 205 s (`serial-1.log`)
- Run 2: target hit after 206 s (`serial-2.log`)
- Run 3: target hit after 206 s (`serial-3.log`)

All three runs reported:

```text
INFO: task ... blocked for more than 143 seconds.
f2fs_write_data_pages+0xfaf/0x14a0
```

A run is counted as a target hit only when a single hung-task report contains
both the `INFO: task ... blocked for more than` line and
`f2fs_write_data_pages` in its call trace. The checker is
`verify-logs.py`:

```sh
python3 verify-logs.py serial-1.log serial-2.log serial-3.log
```

The three serial logs contain zero occurrences of `WARNING in diRead`. The
`TARGET-HIT` labels in `run-*.log` identify the F2FS hung-task target.

No main-pipeline VM or state snapshot was reused for these three runs.
