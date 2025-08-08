from typing import cast

import pytest
from pydantic import ValidationError

from onginred.behavior import KeepAliveConfig, LaunchBehavior


def test_launch_behavior_keep_alive_dict():
    lb = LaunchBehavior(
        run_at_load=True,
        keep_alive={"SuccessfulExit": False},
        path_state={"file": True},
        other_jobs={"job.foo": True},
        crashed=True,
        successful_exit=False,
    )
    d = lb.to_plist_dict()
    assert d["RunAtLoad"] is True
    assert isinstance(d["KeepAlive"], dict)
    assert d["KeepAlive"]["Crashed"] is True


def test_keep_alive_config_as_plist_matrix():
    assert KeepAliveConfig(keep_alive=True).as_plist() is True
    assert KeepAliveConfig(keep_alive={"SuccessfulExit": False}).as_plist() == {"SuccessfulExit": False}
    assert (
        KeepAliveConfig(
            keep_alive=True,
            path_state={"/tmp": True},  # noqa: S108
        ).as_plist()
        == {"PathState": {"/tmp": True}}  # noqa: S108
    )
    assert KeepAliveConfig().as_plist() is None


def test_launch_behavior_negative_exit_timeout():
    lb = LaunchBehavior()
    with pytest.raises(ValidationError):
        lb.exit_timeout = -1


def test_launch_behavior_default_plist():
    assert LaunchBehavior().to_plist_dict() == {}


# Resource Limits and Process Attributes
def test_soft_and_hard_resource_limits():
    lb = LaunchBehavior()
    plist = cast("dict", lb.to_plist_dict())
    plist["SoftResourceLimits"] = {"CPU": 60, "NumberOfFiles": 256}
    plist["HardResourceLimits"] = {"CPU": 120, "NumberOfFiles": 512}
    assert plist["SoftResourceLimits"]["CPU"] == 60
    assert plist["HardResourceLimits"]["NumberOfFiles"] == 512


def test_process_type_and_nice():
    lb = LaunchBehavior()
    plist = cast("dict", lb.to_plist_dict())
    plist["ProcessType"] = "Interactive"
    plist["Nice"] = 10
    assert plist["ProcessType"] == "Interactive"
    assert plist["Nice"] == 10


# LaunchOnlyOnce Behavior
def test_launch_only_once_flag():
    lb = LaunchBehavior()
    lb.launch_only_once = True
    plist = lb.to_plist_dict()
    assert plist["LaunchOnlyOnce"] is True


def test_enable_transactions_and_pressured_exit_flags():
    lb = LaunchBehavior(enable_transactions=True, enable_pressured_exit=True)
    d = lb.to_plist_dict()
    assert d["EnableTransactions"] is True
    assert d["EnablePressuredExit"] is True


def test_launch_behavior_negative_throttle_interval():
    lb = LaunchBehavior()
    with pytest.raises(ValidationError):
        lb.throttle_interval = -10


def test_launch_behavior_zero_exit_timeout_is_valid():
    lb = LaunchBehavior()
    lb.exit_timeout = 0
    assert lb.to_plist_dict()["ExitTimeout"] == 0
