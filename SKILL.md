---
name: agnes-image-video-generator
description: Generate or edit images with Agnes Image 2.0 Flash and generate, animate, poll, and download videos with Agnes Video V2.0 through the Agnes AI API. Uses curl.exe without forcing proxy bypass, allowing the current curl configuration, proxy environment, Clash TUN, and system routing to determine the connection path. Use for Agnes image/video generation, editing, composition, text-to-video, image-to-video, or keyframe animation, including Chinese requests such as 用 Agnes 生成图片、图片编辑、文生视频、图生视频、关键帧视频.
---

# Agnes Image & Video Generator — observable curl transport

Use only the bundled client. Do not create ad-hoc urllib/curl test scripts during a media request. Do not speculate about failures without showing the bundled client's actual output.

The client emits a start line and a heartbeat every 15 seconds while Agnes is generating or an output is downloading. A long-running request with heartbeat output is not a silent failure.

The Agnes API is OpenAI-compatible, requires Bearer API-key authentication, and uses `https://apihub.agnes-ai.com/v1` as its Base URL.

## Agent execution contract

For every user media request:

1. Build one prompt that preserves the user's stated subject and constraints. Do not add an age, ethnicity, nationality, gender, identity, or named person unless the user supplied it or it is necessary to satisfy the request.
2. Choose a new output filename for the current request. Never treat a file from an earlier run as proof that the current run succeeded.
3. Invoke the absolute `agnes.ps1` wrapper exactly once for the generation attempt. Do not replace it with inline Python, heredocs, `urllib`, or an independently constructed REST call.
4. While the command is running, rely on the emitted `agnes: ... still running` heartbeat. Do not terminate or diagnose it merely because generation takes time.
5. On success, report the returned `url` and the saved `output` path.
6. If generation succeeds but download fails, report the generated URL preserved in the exact error line. Do not describe the whole request as a generation failure.
7. On failure, quote the exact final `error:` or `unexpected error:` line and the exit code. Never invent empty stdout, hidden exceptions, quota issues, permissions, regional restrictions, or service outages without corresponding output.
8. Do not present a generic troubleshooting essay when the bundled client has produced a concrete result or error.

## Windows network behavior

The client uses `curl.exe` for all API requests and result downloads and keeps HTTP/1.1 enabled for compatibility.

It does **not** add `--noproxy "*"`, does not force direct access, and does not override the user's proxy or routing configuration. Connection routing is therefore determined by the current curl environment and operating system network path, including:

- curl proxy environment variables such as `HTTPS_PROXY`, `ALL_PROXY`, and `NO_PROXY`;
- curl configuration files;
- Clash Verge TUN routing;
- the current Windows network route.

The API key is sent to curl through stdin configuration rather than being exposed in the command line.

## Always use the absolute wrapper on Windows

```powershell
& "$env:USERPROFILE\.workbuddy\skills\agnes-image-video-generator\scripts\agnes.ps1" diagnose
```

Generate an image:

```powershell
& "$env:USERPROFILE\.workbuddy\skills\agnes-image-video-generator\scripts\agnes.ps1" image `
  --prompt "A cyberpunk city at night, neon lights, cinematic, highly detailed" `
  --size 1024x1024 `
  --output "$PWD\agnes-output.png"
```

For image editing or composition, repeat `--input`. Local files are converted to Data URIs in memory.

```powershell
& "$env:USERPROFILE\.workbuddy\skills\agnes-image-video-generator\scripts\agnes.ps1" image `
  --prompt "Keep the subject unchanged and replace the background with a futuristic city" `
  --input "$PWD\input.png" `
  --output "$PWD\edited.png"
```

Generate and poll a video:

```powershell
& "$env:USERPROFILE\.workbuddy\skills\agnes-image-video-generator\scripts\agnes.ps1" video `
  --prompt "A cat walking on a beach at sunset, slow tracking shot" `
  --num-frames 121 `
  --frame-rate 24 `
  --poll `
  --output "$PWD\output.mp4"
```

## Required behavior

- Read the key only from `AGNES_API_KEY`.
- Restart WorkBuddy after changing the environment variable or replacing the Skill.
- Use the bundled wrapper/client only; do not substitute inline Python.
- Do not force `--noproxy "*"` or otherwise override the user's proxy/routing configuration.
- Do not claim success unless the current invocation returns a valid result and, when `--output` is supplied, the newly written file exists.
- Do not infer current success from a pre-existing image in the workspace.
- On failure, report the exact visible `error:` or `unexpected error:` line and exit code.
- If an `agnes: image generated; url=...` line appeared before a download error, preserve and report that URL.
- Do not produce a generic troubleshooting essay in place of actual command output.
- Image model: `agnes-image-2.0-flash`.
- Image endpoint: `POST /v1/images/generations`.
- Put `response_format` and image inputs inside `extra_body`.
- Video model: `agnes-video-v2.0`.
- `num_frames <= 441` and follows `8n + 1`.
- Never print, save, or commit the API key.

Read `references/api.md` and `references/network.md` for the API contract and network behavior.
