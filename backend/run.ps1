$ErrorActionPreference = "Stop"
$resourceName = "CARIC$([char]0x6A21)$([char]0x578B)&$([char]0x6570)$([char]0x636E)$([char]0x96C6)"
$env:ANTI_FRAUD_RESOURCE_ROOT = Join-Path "D:\" $resourceName
$env:ANTI_FRAUD_OCR_PRELOAD = "1"
$env:ANTI_FRAUD_OCR_DET_MODEL = "PP-OCRv5_mobile_det"
$env:ANTI_FRAUD_OCR_REC_MODEL = "PP-OCRv5_mobile_rec"
$env:ANTI_FRAUD_OCR_DET_LIMIT_SIDE_LEN = "960"
$env:ANTI_FRAUD_OCR_FAST_ANALYSIS = "1"
$env:ANTI_FRAUD_QWEN_ENABLED = "1"
$env:ANTI_FRAUD_QWEN_PRELOAD = "1"
$env:ANTI_FRAUD_QWEN_MAX_NEW_TOKENS = "80"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
