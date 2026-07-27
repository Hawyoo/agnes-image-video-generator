# Agnes API contract

Sources checked on 2026-07-27:

- https://agnes-ai.com/doc/overview
- Agnes model-specific image/video documentation referenced by the overview
- Successful local request to the image endpoint returning HTTP 200 and a downloadable output URL

## Shared settings

- Base URL: `https://apihub.agnes-ai.com/v1`
- Authentication: `Authorization: Bearer $AGNES_API_KEY`
- Interface style: OpenAI-compatible

## Image

- Model: `agnes-image-2.0-flash`
- Endpoint: `POST https://apihub.agnes-ai.com/v1/images/generations`
- Request fields used by this Skill:
  - `model`
  - `prompt`
  - `size`
  - `extra_body.response_format`
  - optional `extra_body.image`
- The first result may contain `data[0].url` or `data[0].b64_json`.

## Video

- Model: `agnes-video-v2.0`
- Create endpoint: `POST https://apihub.agnes-ai.com/v1/videos`
- Poll endpoint used by this Skill: `GET https://apihub.agnes-ai.com/agnesapi?video_id=...&model_name=...`
- Completed output URL: `metadata.url`
- Frame rule: `num_frames <= 441` and `num_frames = 8n + 1`
- Frame rate: 1 through 60

## Security

Never embed the API key in the Skill, command history, logs, screenshots, or repositories. The bundled client sends the Authorization header to curl through stdin configuration so the key does not appear in the curl process command line.
