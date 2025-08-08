"""Launchd behaviour configuration."""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field

from onginred.utils import to_camel

__all__ = ["KeepAliveConfig", "LaunchBehavior"]


class KeepAliveConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    keep_alive: bool | dict | None = None
    path_state: dict[str, bool] = Field(default_factory=dict)
    other_jobs: dict[str, bool] = Field(default_factory=dict, alias="OtherJobEnabled")
    crashed: bool | None = None
    successful_exit: bool | None = None

    def _base_from_keep_alive(self) -> dict | None:
        """Derive the initial dictionary from ``keep_alive``."""
        if isinstance(self.keep_alive, dict):
            return dict(self.keep_alive)
        if self.keep_alive is True:
            return {}
        return None

    def _merge_optional(self, base: dict | None) -> dict | None:
        """Merge optional configuration fields into ``base``."""
        if self.path_state:
            base = base or {}
            base["PathState"] = self.path_state
        if self.other_jobs:
            base = base or {}
            base["OtherJobEnabled"] = self.other_jobs
        if self.crashed is not None:
            base = base or {}
            base["Crashed"] = self.crashed
        if self.successful_exit is not None:
            base = base or {}
            base["SuccessfulExit"] = self.successful_exit
        return base

    def as_plist(self) -> bool | dict | None:
        """Return the launchd ``KeepAlive`` representation."""
        base = self._base_from_keep_alive()
        base = self._merge_optional(base)
        if base is None:
            return None
        if self.keep_alive is True and not base:
            return True
        return base


class LaunchBehavior(BaseModel):
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True, alias_generator=to_camel)

    run_at_load: bool | None = None
    enable_pressured_exit: bool | None = None
    enable_transactions: bool | None = None
    launch_only_once: bool | None = None
    exit_timeout: int | None = Field(None, ge=0)
    throttle_interval: int | None = Field(None, ge=0)
    keep_alive: bool | dict | None = None
    path_state: dict[str, bool] = Field(default_factory=dict)
    other_jobs: dict[str, bool] = Field(default_factory=dict)
    crashed: bool | None = None
    successful_exit: bool | None = None

    class BehaviorPlist(TypedDict, total=False):
        """Typed dictionary returned from :meth:`to_plist_dict`."""

        RunAtLoad: bool
        EnablePressuredExit: bool
        EnableTransactions: bool
        LaunchOnlyOnce: bool
        ExitTimeout: int
        ThrottleInterval: int
        KeepAlive: bool | dict

    def to_plist_dict(self) -> BehaviorPlist:
        plist = self.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude={
                "keep_alive",
                "path_state",
                "other_jobs",
                "crashed",
                "successful_exit",
            },
        )
        kab = KeepAliveConfig(
            keep_alive=self.keep_alive,
            path_state=self.path_state,
            other_jobs=self.other_jobs,
            crashed=self.crashed,
            successful_exit=self.successful_exit,
        )
        ka = kab.as_plist()
        if ka is not None:
            plist["KeepAlive"] = ka
        return plist  # type: ignore[return-value]
