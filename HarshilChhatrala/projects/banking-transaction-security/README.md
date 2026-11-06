# Multi-Layer Banking Transaction Security Pipeline

An educational sender-to-receiver file/message protection pipeline demonstrating multiple cryptographic security layers.

## Demonstrated concepts
- AES symmetric encryption
- RSA-OAEP session-key wrapping (hybrid encryption)
- SHA-256 integrity hashing
- RSA-PSS digital signatures
- Certificate handling
- A simplified Kerberos-style authentication exchange
- Tampering and verification demonstrations

## Tech Stack
Python, `cryptography`, Pillow, matplotlib, JSON, CSV.

## Setup and run
```bash
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
python secure_pipeline.py --message "Example transaction message"
```

See the script's command-line help for supported inputs and options.

## Security and privacy
Generated keys, certificates, encrypted output, transaction CSV files, and execution logs are not committed. Use synthetic test data only. This is a coursework demonstration and must not be used to secure real banking transactions without a professional security review.
