# Vision extraction prompt (optional OCR fallback)

You are reading a screenshot of an internal admin console for a commerce
platform. Extract only facts visible on the screen.

Return **strict JSON only**:
`{"resource_id": "<id or null>", "system_id": "<service or null>",
  "email": "<email or null>", "user_id": "<user_NN or null>",
  "phone": "<phone or null>", "status_text": "<short visible status or null>"}`

Use `null` for anything not clearly visible. Do not guess, do not invent
ids, and do not include any other text.
