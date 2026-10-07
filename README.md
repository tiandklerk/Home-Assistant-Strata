# Strata for Home Assistant

A [HACS](https://hacs.xyz) custom integration for [Strata](https://github.com/Niko1221/Strata), the local LLM server that
runs a large model on your own gaming PC.

- **Assist conversation agent**: use Strata as the brain of your voice assistant, optionally with control of your devices.
- **Status sensors**: state (idle / reading / writing / unloaded), answer and prompt speed, requests, queue, GPU load,
  temperature, power, VRAM and RAM use, uptime, context size.
- **Model loaded / busy** binary sensors.
- **Load / unload buttons**: free the GPU for a game with one press (for example from an automation).

Everything stays on your network.

## Install

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/tiandklerk/Home-Assistant-Strata`, type **Integration**.
2. Install **Strata**, restart Home Assistant.
3. **Settings → Devices & services → Add integration → Strata**.

## Make Strata reachable

By default Strata listens on `127.0.0.1` only. On the PC that runs it, start it so other devices can connect, with a key:

```
START-HERE.bat --setup --host 0.0.0.0 --api-key <secret>
```

(Linux: `./setup.sh --setup --host 0.0.0.0 --api-key <secret>`). Then enter the PC's IP address, port `8080` and the key
in Home Assistant. Allow the port in the PC's firewall. Don't expose Strata to the internet.

## Use it as a voice assistant

**Settings → Voice assistants →** pick your assistant → set **Conversation agent** to **Strata**.
Open the integration's **Configure** to set the instructions, the answer length and whether the model may control
Home Assistant (**Control Home Assistant → Assist**). Tool calling needs a model that supports it; the first answer
after Strata was idle can take a while if the model has to be loaded.

## Notes

- Strata answers one request at a time; others wait their turn (see the *Queued requests* sensor).
- *Load model* / *Unload model* return an error while a request is running.
- Sensors use `/v1/status` and `/metrics`. GPU/RAM sensors are empty if Strata has no hardware telemetry.
