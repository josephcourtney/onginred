# CLI Usage

## Commands

```bash
onginred scaffold <label> <command...> [--output path]
onginred inspect <plist-path>
onginred install <label> [options] [-- command args...]
onginred uninstall <label> [--plist-path path]
````

---

## Example 1: Timed job (every 5 minutes + run at load)

This job runs a script every 5 minutes, logs output to `~/Library/Logs`, and starts immediately on load.

### 0) Create the script

```bash
mkdir -p "$HOME/bin" "$HOME/Library/Logs"
cat > "$HOME/bin/hello.sh" <<'SH'
#!/bin/sh
echo "[$(date '+%Y-%m-%d %H:%M:%S')] hello from launchd" >> "$HOME/Library/Logs/hello.log"
SH
chmod +x "$HOME/bin/hello.sh"
```

### 1) Install & load

```bash
onginred install com.example.hello \
  --run-at-load \
  --start-interval 300 \
  --log-dir "$HOME/Library/Logs" \
  --create-log-files \
  -- "$HOME/bin/hello.sh"
```

### 2) Check logs

```bash
tail -n 5 "$HOME/Library/Logs/hello.log"
```

### 3) Uninstall

```bash
onginred uninstall com.example.hello
```

---

## Example 2: File-watching job

Runs whenever files change in a watched directory or are added to a queue directory.

### 0) Create watch dirs and script

```bash
mkdir -p "$HOME/tmp/watch_here" "$HOME/tmp/queue_here" "$HOME/bin" "$HOME/Library/Logs"
cat > "$HOME/bin/onchange.sh" <<'SH'
#!/bin/sh
echo "[$(date '+%Y-%m-%d %H:%M:%S')] change detected in $1" >> "$HOME/Library/Logs/onchange.log"
SH
chmod +x "$HOME/bin/onchange.sh"
```

### 1) Install & load

```bash
onginred install com.example.onchange \
  --run-at-load \
  --watch "$HOME/tmp/watch_here" \
  --queue "$HOME/tmp/queue_here" \
  --log-dir "$HOME/Library/Logs" \
  --create-log-files \
  -- "$HOME/bin/onchange.sh"
```

### 2) Trigger it

```bash
touch "$HOME/tmp/watch_here/file1"
touch "$HOME/tmp/queue_here/job1"
```

### 3) Check logs

```bash
tail -n 5 "$HOME/Library/Logs/onchange.log"
```

### 4) Uninstall

```bash
onginred uninstall com.example.onchange
```

