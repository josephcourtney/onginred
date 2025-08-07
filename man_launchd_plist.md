# `launchd.plist``man`Page

## Name
launchd.plist – System wide and per-user daemon/agent configuration files

## Description
This document details the parameters that can be given to an XML property list that can be loaded into launchd with launchctl.

## Expectations
Daemons or agents managed by launchd are expected to behave certain ways.
A daemon or agent launched by launchd MUST NOT do the following in the process directly launched by launchd:
 - Call `daemon(3)`.
 - Do the moral equivalent of daemon(3) by calling `fork(2)`and have the parent process `exit(3)`or `_exit(2)`.
A launchd daemon or agent should not perform the following as part of its initialization, as launchd will always implicitly perform them on behalf of the process.
 - Redirect `stdio(3)`to `/dev/null`.
A launchd daemon or agent need not perform the following as part of its initialization, since launchd can perform them on the process' behalf with the appropriate launchd.plist keys specified.
 - Setup the user ID or group ID.
 - Setup the working directory.
 - `chroot(2)`
 - `setsid(2)`
 - Close "stray" file descriptors.
 - Setup resource limits with `setrlimit(2)`.
 - Setup priority with `setpriority(2)`.
A daemon or agent launched by launchd SHOULD:
 - Launch on demand given criteria specified in the XML property list. More information can be found
          later in this man page.
 - Handle the SIGTERM signal, preferably with a `dispatch(3)`source, and respond to this signal by
          unwinding any outstanding work quickly and then exiting.
A daemon or agent launched by launchd MUST:
 - check in for any MachServices advertised in its plist, using `xpc_connection_create_mach_service(3)`(or `bootstrap_check_in(3)`) if it uses MIG or raw Mach for communication
 - check in for any LaunchEvents advertised in its plist, using `xpc_set_event_stream_handler(3)`

## Xml Property List Keys
The following keys can be used to describe the configuration details of your daemon or agent. Property lists are Apple's standard configuration file format. Please see `plist(5)`for more information. Please note: property list files are expected to have their name end in ".plist". Also please note that it is the expected convention for launchd property list files to be named \<Label\>.plist. Thus, if your job label is "com.apple.sshd", your plist file should be named "com.apple.sshd.plist".

| Key                         | Type                                                              | Description                                                                        | Required      |
| --------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------- |
| Label                       | string                                                            | Unique identifier for the job.                                                     | Yes           |
| Disabled                    | boolean                                                           | If true, job is not loaded by default. Its state is kept externally and can be overridden by `launchctl enable`.                                              | No       |
| UserName                    | string                                                            | User account under which to run the job (system domain only). If `GroupName` is unset, group defaults to the user's primary group.                            | No       |
| GroupName                   | string                                                            | Group under which to run the job (system domain only). Defaults to UserName's primary group when unset.                                                       | No       |
| Wait                        | boolean                                                           | If true, pass listening socket on stdio; if false, accept() is handled by launchd. | No            |
| LimitLoadToSessionType      | string or array of strings                                        | Restrict loading to these session types (agents only).                             | No            |
| LimitLoadToHardware         | dictionary of arrays                                              | Restrict loading to machines matching these hw.sysctl values.                     | No            |
| LimitLoadFromHardware       | dictionary of arrays                                              | Prevent loading on machines matching these hw.sysctl values.                      | No            |
| Program                     | string                                                            | Absolute path to executable (first argument to execv). Must be absolute; if missing, first `ProgramArguments` entry is used and resolved via `_PATH_STDPATH`. | Cond.¹   |
| BundleProgram               | string                                                            | App-bundle relative path to executable (SMAppService only).                        | No            |
| ProgramArguments            | array of strings                                                  | `argv` array passed to the executable. Relative paths are resolved via `_PATH_STDPATH`.                                                                       | Cond.¹   |
| EnableGlobbing              | boolean                                                           | Expand wildcard patterns in ProgramArguments.                                      | No            |
| EnableTransactions          | boolean                                                           | Track XPC transactions to determine process activity.                              | No            |
| EnablePressuredExit         | boolean                                                           | Opt into low-memory kill when inactive and automatic relaunch on exit.             | No            |
| OnDemand                    | boolean                                                           | Alias for KeepAlive; should be removed.                                            | No            |
| KeepAlive                   | boolean or dictionary                                             | Relaunch job on exit when true or when conditions match. Rapid successive exits are automatically throttled.                                                  | No       |
| SuccessfulExit              | boolean                                                           | Relaunch on zero exit status. Implies `RunAtLoad=true` so the job runs at least once before checking exit status.                                             | No       |
| PathState                   | dictionary of booleans                                            | Keep job alive based on file existence or nonexistence. Filesystem monitoring is race-prone; IPC-based triggers are preferred.                                | No       |
| OtherJobEnabled             | dictionary of booleans                                            | Keep job alive while specified jobs are loaded.                                    | No            |
| Crashed                     | boolean                                                           | Relaunch when job exits due to a crash signal.                                     | No            |
| RunAtLoad                   | boolean                                                           | Launch job immediately when loaded. Default false; speculative launches can slow boot and login performance.                                                  | No       |
| RootDirectory               | string                                                            | chroot to this directory before running.                                           | No            |
| WorkingDirectory            | string                                                            | chdir to this directory before running.                                            | No            |
| EnvironmentVariables        | dictionary of strings                                             | Set these environment variables before running.                                    | No            |
| Umask                       | integer or string                                                 | `umask` value to apply before running. Integers are decimal; strings are parsed by `strtoul`, allowing octal (e.g. `"0755"`).                                 | No       |
| ExitTimeOut                 | integer                                                           | Seconds between SIGTERM and SIGKILL on stop.                                       | No            |
| ThrottleInterval            | integer                                                           | Minimum seconds between automatic relaunches. (Default 10s)                                      | No            |
| InitGroups                  | boolean                                                           | Call `initgroups()` before running (if `UserName` set). Ignored if `UserName` is unset.                                                                       | No       |
| WatchPaths                  | array of strings                                                  | Launch when any specified file-system path is modified. Filesystem event monitoring is race-prone and may see inconsistent file states.                       | No       |
| QueueDirectories            | array of strings                                                  | Keep job alive while specified directories are non-empty.                          | No            |
| StartOnMount                | boolean                                                           | Launch job on every filesystem mount.                                              | No            |
| StartInterval               | integer                                                           | Launch job every N seconds. Intervals missed during sleep or while the job is already running are dropped.                                                    | No       |
| StartCalendarInterval       | dict or array of dicts                                            | Dictionary or array of dictionaries mapping calendar fields (minute, hour, day, weekday, month) to launch times; unspecified fields act as wildcards. Missed firings while the Mac is asleep or the job is already running coalesce into a single launch when it wakes.                            | No       |
| Minute                      | integer                                                           | Minute (0–59) for StartCalendarInterval.                                           | No            |
| Hour                        | integer                                                           | Hour (0–23) for StartCalendarInterval.                                             | No            |
| Day                         | integer                                                           | Day of month (1–31) for StartCalendarInterval.                                     | No            |
| Weekday                     | integer                                                           | Weekday (0=Sun–7=Sun) for StartCalendarInterval.                                   | No            |
| Month                       | integer                                                           | Month (1–12) for StartCalendarInterval.                                            | No            |
| StandardInPath              | string                                                            | Redirect stdin from this file.                                                     | No            |
| StandardOutPath             | string                                                            | Redirect stdout to this file. If missing, no redirection. File is created with ownership from `UserName`/`GroupName` and permissions from `Umask`.            | No       |
| StandardErrorPath           | string                                                            | Redirect stderr to this file. File is created with ownership from `UserName`/`GroupName` and permissions from `Umask`.                                        | No       |
| Debug                       | boolean                                                           | Enable LOG\_DEBUG for this job.                                                    | No            |
| WaitForDebugger             | boolean                                                           | Start job suspended to allow debugger attachment.                                  | No            |
| SoftResourceLimits          | dictionary of integers                                            | Set soft RLIMIT values before running.                                             | No            |
| HardResourceLimits          | dictionary of integers                                            | Set hard RLIMIT values before running.                                             | No            |
| Core                        | integer                                                           | Max core file size.                                                                | No            |
| CPU                         | integer                                                           | Max CPU time in seconds.                                                           | No            |
| Data                        | integer                                                           | Max data segment size.                                                             | No            |
| FileSize                    | integer                                                           | Max file size created.                                                             | No            |
| MemoryLock                  | integer                                                           | Max bytes locked into memory.                                                      | No            |
| NumberOfFiles               | integer                                                           | Max open file descriptors.                                                         | No            |
| NumberOfProcesses           | integer                                                           | Max processes per UID.                                                             | No            |
| ResidentSetSize             | integer                                                           | Max resident memory size.                                                          | No            |
| Stack                       | integer                                                           | Max stack size.                                                                    | No            |
| Nice                        | integer                                                           | nice value to apply.                                                               | No            |
| ProcessType                 | string                                                            | High-level classification: Background, Standard, Adaptive, or Interactive. See [[Valid Values for `ProcessType`]] for details.         | No            |
| AbandonProcessGroup         | boolean                                                           | Do not kill sibling processes in same process group.                               | No            |
| LowPriorityIO               | boolean                                                           | Throttle filesystem I/O priority.                                                  | No            |
| LowPriorityBackgroundIO     | boolean                                                           | Throttle I/O priority when in background.                                          | No            |
| MaterializeDatalessFiles    | boolean                                                           | Materialize on-demand "dataless" files.                                            | No            |
| LaunchOnlyOnce              | boolean                                                           | Allow only a single run without reboot.                                            | No            |
| MachServices                | boolean or nested dictionary                                      | Advertise Mach services at launch.                                                 | No            |
| ResetAtClose                | boolean                                                           | Force port death notifications on MachServices reset.                              | No            |
| HideUntilCheckIn            | boolean                                                           | Keep Mach service hidden until job calls bootstrap\_check\_in().                   | No            |
| Sockets                     | dictionary of dictionaries or dictionary of array of dictionaries | Define sockets for launch-on-demand. See [[Sock Property List Keys]] for details.   | No            |
| Bonjour                     | boolean, string, or array of strings                              | Register service with Bonjour using given name(s).                                 | No            |
| MulticastGroup              | string                                                            | Join this multicast group on UDP sockets. If given as an explicit IP, `SockFamily` must also be set to match the address family.                              | No       |
| LaunchEvents                | dictionary of dictionaries of dictionaries                        | Launch on specified I/O Kit or other system events.                                | No            |
| SessionCreate               | boolean                                                           | Spawn job in new audit session.                                                    | No            |
| LegacyTimers                | boolean                                                           | Opt out of timer coalescing (more precise).                                        | No            |
| AssociatedBundleIdentifiers | string or array of strings                                        | Bundle IDs to expose in Login Items UI.                                            | No            |

^[1]: Either `Program` or `ProgramArguments` must be present; if both are present, `Program` defines the executable path.

### `Sock` Property List Keys
| Key                         | Type                                                              | Description                                                                        | Required      |
| --------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------- |
| SockType                    | string                                                            | Socket type: stream, dgram, or seqpacket.                                          | No            |
| SockPassive                 | boolean                                                           | If true, call listen(); if false, call connect().                                  | No            |
| SockNodeName                | string                                                            | Hostname or IP to bind or connect.                                                 | No            |
| SockServiceName             | string or integer                                                 | Service name or port number.                                                       | No            |
| SockFamily                  | string                                                            | Address family: IPv4, IPv6, or IPv4v6.                                             | No            |
| SockProtocol                | string                                                            | Protocol: TCP or UDP.                                                              | No            |
| SockPathName                | string                                                            | UNIX-domain socket path.                                                           | No            |
| SecureSocketWithKey         | string                                                            | Generate secure UNIX socket and set path in environment.                           | No            |
| SockPathOwner               | integer                                                           | UID to own UNIX-domain socket.                                                     | No            |
| SockPathGroup               | integer                                                           | GID to own UNIX-domain socket.                                                     | No            |
| SockPathMode                | integer                                                           | Mode (octal as decimal) for UNIX socket.                                           | No            |

### Valid Values for `ProcessType`
  - `Background`: Background jobs are generally processes that do work that was not directly requested by the user. The resource limits applied to Background jobs are intended to prevent them from disrupting the user experience.
  - `Standard`: Standard jobs are equivalent to no ProcessType being set.
  - `Adaptive`: Adaptive jobs move between the Background and Interactive classifications based on activity over XPC connections. See `xpc_transaction_begin(3)`for details.
  - `Interactive`: Interactive jobs run with the same resource limitations as apps, that is to say, none. Interactive jobs are critical to maintaining a responsive user experience, and this key should only be used if an app's ability to be responsive depends on it, and cannot be made Adaptive.

## Example
The following XML Property List describes an on-demand daemon that will only launch when a message arrives on the "com.example.exampled" MachService.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN"
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
	<dict>
		<key>Label</key>
		<string>com.example.exampled</string>
		<key>Program</key>
		<string>/path/tp/exampled</string>
		<key>ProgramArguments</key>
		<array>
			<string>exampled</string>
			<string>argv1</string>
			<string>argv2</string>
		</array>
		<key>MachServices</key>
		<dict>
			<key>com.example.exampled</key>
			<true/>
		</dict>
	</dict>
</plist>
```

## Files
- `~/Library/LaunchAgents`: Per-user agents provided by the user.
- `/Library/LaunchAgents`: Per-user agents provided by the administrator.
- `/Library/LaunchDaemons`: System-wide daemons provided by the administrator.
- `/System/Library/LaunchAgents`: Per-user agents provided by OS X.
- `/System/Library/LaunchDaemons`: System-wide daemons provided by OS X.
