from onginred.builder import LaunchdBuilder


def test_builder_chain() -> None:
    builder = LaunchdBuilder()
    sched = (
        builder.cron("0 12 * * *")
        .at(8, 30)
        .watch("/tmp/foo")  # noqa: S108
        .queue("/tmp/bar")  # noqa: S108
        .keep_alive()
        .build()
    )

    assert {"Minute": 30, "Hour": 8} in sched.time.calendar_entries
    assert "/tmp/foo" in sched.fs.watch_paths  # noqa: S108
    assert "/tmp/bar" in sched.fs.queue_directories  # noqa: S108
    assert sched.behavior.keep_alive is True
