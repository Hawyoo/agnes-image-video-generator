# agnes-image-video-generator

A WorkBuddy/agent Skill for generating and editing images with **Agnes Image 2.0 Flash**, and generating, polling, and downloading videos with **Agnes Video V2.0**.

The bundled client uses Windows `curl.exe` with visible progress heartbeats and exact error reporting. It does not force proxy bypass; the active curl configuration, proxy environment, Clash TUN routing, and Windows network route determine the connection path.

## Features

- Text-to-image generation
- Image editing and multi-image composition
- Text-to-video generation
- Image-to-video generation
- Keyframe video generation
- Video task polling and result download
- Visible heartbeat output for long-running requests
- Preserves a generated media URL if local download fails

## Installation

1. Download the release ZIP or clone this repository.
2. Copy the repository folder to:

   ```text
   %USERPROFILE%\.workbuddy\skills\agnes-image-video-generator
   ```

3. Set your Agnes API key as an environment variable:

   ```powershell
   setx AGNES_API_KEY "your-api-key"
   ```

4. Fully restart WorkBuddy after changing the environment variable or replacing the Skill.

## Diagnose

```powershell
& "$env:USERPROFILE\.workbuddy\skills\agnes-image-video-generator\scripts\agnes.ps1" diagnose
```

## Generate an image

```powershell
& "$env:USERPROFILE\.workbuddy\skills\agnes-image-video-generator\scripts\agnes.ps1" image `
  --prompt "A cyberpunk city at night, neon lights, cinematic, highly detailed" `
  --size 1024x1024 `
  --output "$PWD\agnes-output.png"
```

## Edit an image

```powershell
& "$env:USERPROFILE\.workbuddy\skills\agnes-image-video-generator\scripts\agnes.ps1" image `
  --prompt "Keep the subject unchanged and replace the background with a futuristic city" `
  --input "$PWD\input.png" `
  --output "$PWD\edited.png"
```

## Generate and poll a video

```powershell
& "$env:USERPROFILE\.workbuddy\skills\agnes-image-video-generator\scripts\agnes.ps1" video `
  --prompt "A cat walking on a beach at sunset, slow tracking shot" `
  --num-frames 121 `
  --frame-rate 24 `
  --poll `
  --output "$PWD\output.mp4"
```

## Network behavior

This Skill does not add `--noproxy "*"` and does not force a direct or proxied connection. Routing is determined by the user's current network configuration, including curl proxy environment variables, curl configuration files, Clash Verge TUN routing, and Windows routes.

See [`references/network.md`](references/network.md) for details.

## Security

- The API key is read only from `AGNES_API_KEY`.
- Never commit an API key to this repository.
- The client passes authorization data to curl through stdin configuration rather than including the key in the process command line.

## API documentation

- Agnes API overview: `https://agnes-ai.com/doc/overview`
- Base URL: `https://apihub.agnes-ai.com/v1`

## License

No license has been assigned yet. Add one before redistributing if needed.
