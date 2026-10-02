# Handoff 02 — ThoxMini host provisioning and USB bench

**Owner:** Mini/Linux firmware engineer.  
**Repository:** <https://github.com/ttracx/thox-usbmuxd>  
**Work branch base:** current `origin/master`; implemented reference baseline `af3372806f01a572f08105552f6072af0a2c4de2`.  
**Current evidence:** the delivery owner reports 34 passing Python tests at this baseline. That evidence covers host/protocol software; it does not establish a flashable image, successful iPhone enumeration, working power topology, or a signed iOS build.

## Assignment

Turn the manually launched Mini host POC into reproducible, reversible Linux provisioning, then qualify one exact ThoxMini/iPhone hardware combination. Deliver the package installation/provisioning scripts, service units, operator recovery instructions, and a completed bench record. Produce a flashable image only after the target board, OS image, USB data role, partition layout, and recovery method are recorded; no flash image exists in this baseline.

The vertical slice is the foreground ThoxOS iOS companion → authenticated session → Mini job store → result recovery. Mini initiates the transport connection. `iproxy` exposes host loopback port `49322` and forwards to the iOS application's loopback listener on `49321`. The phone then sends requests over that established connection. This is distinct from configuring Mini as a USB gadget or exposing a Mini HTTP server to iOS.

## Existing code and owned changes

| Existing source | Current responsibility |
|---|---|
| `poc/host/thox_usb/__main__.py` | Pairing-key creation, loopback connection/reconnect loop, host CLI |
| `poc/host/thox_usb/jobs.py` | Private SQLite workspace, one worker, 16 queued jobs, artifacts, optional local inference |
| `poc/host/thox_usb/protocol.py` | Application authentication/encryption; coordinate changes with security owner |
| `poc/host/requirements.txt` | `cryptography==46.0.0`; Python minimum is 3.10 in `pyproject.toml` |
| `poc/docs/BENCH_VALIDATION.md` | B01–B16 physical acceptance record, currently NOT RUN |
| `README.md` | Working manual installation, pairing, forwarding, and launch instructions |

Suggested new paths owned by this task:

- `poc/firmware/`: target manifest, OS/boot configuration notes, image recipe when qualified.
- `poc/deploy/systemd/`: bridge and selected-device forwarding units.
- `poc/scripts/provision-mini.sh`: idempotent setup with explicit target/configuration, verification, and rollback instructions.
- `poc/docs/MINI_OPERATIONS.md`: install, upgrade, restart, rotation, data backup/retention, and recovery instructions.
- `poc/evidence/mini-host/`: redacted measurements, command output, and the exact tested revision.

Coordinate changes to shared host code and `poc/PROTOCOL.md` with the security owner. Leave iOS implementation to its owner. Preserve upstream daemon source and existing notices. Run checks locally; do not add GitHub Actions.

## Dependencies and decisions to close

1. **Hardware:** identify the actual board/revision, enclosure port board, USB-C/OTG wiring, cable/adapter, power supply, and storage image. If testing the Pi Zero 2 W Mini variant, record its actual OS architecture and memory; the microSD capacity does not establish inference capacity.
2. **iOS owner:** obtain the signed standalone companion on one identified phone. Its listener must be started and the app kept foregrounded. Simulator success cannot substitute for this dependency.
3. **OS packaging:** select one supported Debian/Raspberry Pi OS release, record package versions and architecture, and prove installation of the pinned Python dependency. If a compatible wheel is unavailable, document/build the matching wheel rather than silently changing the dependency pin.
4. **Power/data role:** qualify Mini as USB host before testing application traffic. Record whether phone charging is expected, measured voltage/current under load, brownout behavior, and how conflicting power sources are prevented by the actual circuitry.
5. **Security owner:** agree whether provisioning uses one operator account per device/workspace, the key-rotation behavior, and retained-data handling. The baseline has no fleet enrollment, workspace-to-key binding, or application encryption at rest.

## Start from current master

These commands create an isolated development checkout. They do not alter a connected device or install a service.

```bash
git clone https://github.com/ttracx/thox-usbmuxd.git thox-usbmuxd-mini-host
cd thox-usbmuxd-mini-host
git fetch origin master
git show --no-patch --format=fuller af3372806f01a572f08105552f6072af0a2c4de2
git switch -c agent/mini-host-provisioning origin/master
git rev-parse HEAD
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r poc/host/requirements.txt
PYTHONPATH=poc/host python3 -m unittest discover -s poc/tests -v
python3 poc/scripts/demo.py
```

The demo uses loopback and a simulated iOS peer. Save its result as software evidence, not USB evidence. Tests require permission to create local sockets.

## Establish the manual hardware baseline

On the chosen Debian-family image, where these packages are available:

```bash
sudo apt update
sudo apt install usbmuxd libimobiledevice-utils libusbmuxd-tools python3-venv usbutils
uname -a
python3 -c 'import platform, sys; print(sys.version); print(platform.machine())'
dpkg-query -W usbmuxd libimobiledevice-utils libusbmuxd-tools
usbmuxd --version
iproxy --help
lsusb -t
```

Record the image source/checksum and boot configuration separately. Do not replace the distribution daemon with a source build unless a documented compatibility failure requires it. If a source build is needed, pin its commit, installation prefix, activation method, and rollback path; avoid running two daemons against the same device.

From the repository root, create a new key and private workspace for this bench. The following key command intentionally displays the secret; run it in a private operator terminal, enter it in the app's pairing UI, and exclude that output from evidence logs.

```bash
. .venv/bin/activate
umask 077
mkdir -p "$HOME/.config/thox-usb"
mkdir -p "$HOME/thox-usb-workspace"
chmod 700 "$HOME/thox-usb-workspace"
PYTHONPATH=poc/host python3 -m thox_usb pair \
  --output "$HOME/.config/thox-usb/pair.key" \
  --reveal
idevice_id -l
```

`pair` refuses to overwrite an existing key. For an existing bench, reuse the provisioned key deliberately or follow the security owner's rotation procedure. Application pairing is separate from the phone's normal Apple Trust/accessory flow.

In terminal A, select the intended phone explicitly:

```bash
iproxy -u YOUR_IPHONE_UDID 49322:49321
```

In terminal B, from the repository root:

```bash
. .venv/bin/activate
PYTHONPATH=poc/host python3 -m thox_usb bridge \
  --pair-key "$HOME/.config/thox-usb/pair.key" \
  --workspace "$HOME/thox-usb-workspace" \
  --host 127.0.0.1 \
  --port 49322
```

In terminal C, verify the local listener and file modes without printing the key or documents:

```bash
ss -ltnp '( sport = :49322 )'
stat -c '%a %n' "$HOME/.config/thox-usb/pair.key" "$HOME/thox-usb-workspace"
```

Record the installed `iproxy` syntax and observed bind address. Accept only loopback binding; do not select an arbitrary first device or enable a public forwarding listener. A missing device is a cable/role/power/trust/daemon investigation, not a reason to weaken application authentication.

## Provisioning and service implementation

Implement two separately inspectable services: selected-device forwarding and the Python bridge. Use the distribution's daemon activation where it works. The THOX services should run as a dedicated unprivileged account with a private key/workspace and `UMask=0077`; the Python bridge does not need to run as root.

The service definition must use absolute executable/source paths, a fixed key-file path, a persistent workspace, and the selected UDID from a private configuration file. Do not put the pairing secret in command arguments, environment variables, unit files, or journal output. The installed `iproxy` must retain loopback-only binding. Document ownership/access to the daemon socket separately from access to raw USB devices.

Test service restart on cable loss, app backgrounding, daemon restart, and system boot. Avoid a rapid restart loop when the phone is absent. The bridge already reconnects every two seconds by default and can use `--reconnect`; do not inadvertently layer an aggressive external restart loop over normal retry behavior. Forwarder restarts and bridge restarts have different consequences: restarting the bridge marks unfinished jobs interrupted when it starts again.

Once the proposed units exist, verify them before enabling them on the bench. These paths are deliverables to create, not files present in the baseline:

```bash
systemd-analyze verify poc/deploy/systemd/thox-usb-forward.service \
  poc/deploy/systemd/thox-usb-bridge.service
```

Add a smoke-test command that checks service health, selected UDID, local port binding, and workspace permissions without reading secrets or document content. Document install and rollback commands against the actual filenames/user/path choices you implement.

## Workload and recovery behavior to preserve

- Default `analyze` returns deterministic text statistics and SHA-256; it does not run an LLM.
- `job_submit` uses the request UUID as the durable job ID. Repeating identical text/mode under that UUID returns the same job; a different payload returns `conflict`.
- Completed jobs survive connection loss and bridge restart. Queued/running jobs become `failed` with `interrupted` on process restart; they are not automatically retried.
- Cancellation discards late output and stops the owned inference client subprocess. A separately running inference backend may continue computing.
- The optional provider is an operator-fixed literal-loopback `/v1/chat/completions` URL. Redirects and environment proxies are disabled. The caller cannot choose a URL or model.
- The baseline retains input text, results, and job metadata in unencrypted SQLite, plus unencrypted JSON result artifacts. Permissions are access controls, not encryption. Backup and retention instructions must match this behavior.

Enable model inference only after the chosen model/runtime is installed and qualified on the actual Mini. The existing command is:

```bash
PYTHONPATH=poc/host python3 -m thox_usb bridge \
  --pair-key "$HOME/.config/thox-usb/pair.key" \
  --workspace "$HOME/thox-usb-workspace" \
  --host 127.0.0.1 --port 49322 \
  --inference-url http://127.0.0.1:8080/v1/chat/completions \
  --model YOUR_INSTALLED_MODEL_ID
```

## Acceptance evidence

Complete `poc/docs/BENCH_VALIDATION.md` with the exact candidate commit, OS/kernel/architecture, Python and dependency versions, board/port/cable/power revisions, phone/iOS/app build, and UTC time. Include:

1. Repeatable provisioning of a clean supported image and successful rollback of the THOX additions.
2. Service-unit verification, non-root process ownership, mode `600` key/database/artifacts, mode `700` workspace, explicit UDID, and loopback-only port evidence.
3. B01–B15 results, including 20 unplug/replug cycles, wrong-key rejection, interrupted jobs after restart, and saved-ID recovery when a submission acknowledgement is lost.
4. Peak memory, CPU, temperature, power, and reconnect/job latency for the board under test.
5. B16 with named runtime/model/quantization and measured performance, or the explicit value **NOT CONFIGURED**.
6. For an image deliverable: image checksum, reproducible recipe, partition layout, first-boot procedure, and no baked-in device pairing secrets or retained user documents.

A passing bench applies to the recorded hardware/software combination only. Report unresolved failures and the next owner instead of labeling the source fork production-ready.

## Kickoff prompt

> Take ownership of Mini/Linux provisioning for `ttracx/thox-usbmuxd`, starting from current `origin/master` and retaining `af3372806f01a572f08105552f6072af0a2c4de2` as the reference baseline. Read this handoff, the protocol, the host implementation, and the bench checklist. Implement reproducible setup and separately managed loopback-only iproxy/bridge services using an explicit iPhone UDID and a private workspace. Coordinate protocol/key lifecycle changes with the security owner and obtain the signed foreground app from the iOS owner. Run local tests, then qualify one physical Mini/iPhone configuration and commit its evidence. Deliver source, exact install/rollback commands, updated operations documentation, and measured results; do not claim that a flash image, hardware compatibility, or model performance exists until you have produced and tested it. Keep the shared ecosystem/backlog documents current and do not add GitHub Actions.
