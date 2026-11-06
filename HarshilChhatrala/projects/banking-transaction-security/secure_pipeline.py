#!/usr/bin/env python3
"""
End-to-End Encrypted File / Message Exchange Pipeline  (Sender -> Receiver)
===========================================================================
One program, four phases, every stage prints verifiable output and saves artefacts.

  Phase D  Authentication : X.509 self-signed cert, Kerberos login, RSA-PSS signature
  Phase C  Integrity      : SHA-256 before sending / after decrypting, tamper detection
  Phase A  Symmetric      : AES-128-CBC (3DES comparison, avalanche, ECB-vs-CBC, timing)
  Phase B  Asymmetric     : RSA-OAEP hybrid key wrap, Diffie-Hellman, MITM + fix

Usage
  python secure_pipeline.py                      # generates a sample banking CSV and sends it
  python secure_pipeline.py report.pdf           # send ANY file (text or binary)
  python secure_pipeline.py --message "hello"    # send a short message
  python secure_pipeline.py data.csv --out run1 --skip-experiments

Dependencies:  pip install cryptography pillow matplotlib
"""
import argparse, base64, csv, datetime, hashlib, json, os, random, secrets, statistics, sys, time
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, padding as sympad, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym, utils
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import NameOID

try:  # cryptography >= 43
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
except ImportError:  # older versions
    from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES

AES = algorithms.AES
random.seed(42)


# ======================================================================
# Utilities
# ======================================================================
class Tee:
    """Mirror everything printed to a log file (the 'console log' deliverable)."""
    def __init__(self, path):
        self.f, self.o = open(path, "w", encoding="utf-8"), sys.stdout
    def write(self, s): self.o.write(s); self.f.write(s)
    def flush(self): self.o.flush(); self.f.flush()


def banner(t): print("\n" + "=" * 80 + f"\n{t}\n" + "=" * 80)
def sha256_hex(b): return hashlib.sha256(b).hexdigest()
def b64(b): return base64.b64encode(b).decode()
def unb64(s): return base64.b64decode(s)
def now_utc(): return datetime.datetime.now(datetime.timezone.utc)

RESULTS = []  # (task, description, passed)
def record(task, desc, ok):
    RESULTS.append((task, desc, bool(ok)))
    return ok


# ======================================================================
# Symmetric primitives (AES / 3DES, CBC / ECB)
# ======================================================================
def cbc_encrypt(alg, key, iv, data, pad=True):
    bs = alg.block_size
    if pad:
        p = sympad.PKCS7(bs).padder(); data = p.update(data) + p.finalize()
    e = Cipher(alg(key), modes.CBC(iv)).encryptor()
    return e.update(data) + e.finalize()


def cbc_decrypt(alg, key, iv, ct, unpad=True):
    d = Cipher(alg(key), modes.CBC(iv)).decryptor()
    pt = d.update(ct) + d.finalize()
    if unpad:
        u = sympad.PKCS7(alg.block_size).unpadder(); pt = u.update(pt) + u.finalize()
    return pt


def ecb_encrypt(key, data):
    e = Cipher(AES(key), modes.ECB()).encryptor()
    return e.update(data) + e.finalize()


# ======================================================================
# Public-key primitives
# ======================================================================
OAEP = asym.OAEP(mgf=asym.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
PSS = asym.PSS(mgf=asym.MGF1(hashes.SHA256()), salt_length=asym.PSS.MAX_LENGTH)


def new_rsa(bits=2048): return rsa.generate_private_key(public_exponent=65537, key_size=bits)
def pem_priv(k): return k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
def pem_pub(k): return k.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def sign_digest(priv, digest):
    """Sign an already-computed SHA-256 digest (i.e. 'sign the hash') with RSA-PSS."""
    return priv.sign(digest, PSS, utils.Prehashed(hashes.SHA256()))


def verify_digest(pub, sig, digest):
    try:
        pub.verify(sig, digest, PSS, utils.Prehashed(hashes.SHA256())); return True
    except InvalidSignature:
        return False


def make_self_signed_cert(priv, common_name, org, days=365):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, org)])
    t = now_utc()
    return (x509.CertificateBuilder().subject_name(name).issuer_name(name)       # issuer == subject -> self-signed
            .public_key(priv.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(t - datetime.timedelta(minutes=1)).not_valid_after(t + datetime.timedelta(days=days))
            .sign(priv, hashes.SHA256()))


def cert_fingerprint(cert): return cert.fingerprint(hashes.SHA256()).hex()


def cert_self_signature_ok(cert):
    try:
        cert.public_key().verify(cert.signature, cert.tbs_certificate_bytes, asym.PKCS1v15(), cert.signature_hash_algorithm)
        return True
    except InvalidSignature:
        return False


# ======================================================================
# Kerberos (simplified, real encrypted tickets with AES-GCM)
# ======================================================================
def seal(key, obj):
    n = os.urandom(12)
    return n + AESGCM(key).encrypt(n, json.dumps(obj).encode(), None)


def unseal(key, blob):
    return json.loads(AESGCM(key).decrypt(blob[:12], blob[12:], None))


def pw_key(password, user):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), user.encode(), 100_000, dklen=16)


class KDC:
    """Key Distribution Centre = Authentication Server (AS) + Ticket Granting Server (TGS)."""
    TICKET_LIFE = 300

    def __init__(self, users, services):
        self.users = users                     # name -> long-term key derived from password
        self.services = services               # name -> long-term service key
        self.k_tgs = os.urandom(16)

    def as_req(self, client):
        if client not in self.users: raise KeyError("unknown principal")
        sk = os.urandom(16); exp = time.time() + self.TICKET_LIFE
        tgt = seal(self.k_tgs, {"client": client, "sk": b64(sk), "exp": exp})
        return seal(self.users[client], {"sk": b64(sk), "exp": exp}), tgt

    def tgs_req(self, tgt, authenticator, service):
        t = unseal(self.k_tgs, tgt)
        if t["exp"] < time.time(): raise ValueError("TGT expired")
        a = unseal(unb64(t["sk"]), authenticator)
        if a["client"] != t["client"] or abs(time.time() - a["ts"]) > 60: raise ValueError("bad authenticator")
        sk2 = os.urandom(16); exp = time.time() + self.TICKET_LIFE
        st = seal(self.services[service], {"client": t["client"], "sk": b64(sk2), "exp": exp})
        return seal(unb64(t["sk"]), {"sk": b64(sk2), "service": service}), st


class ServiceServer:
    """The Receiver's server: only serves clients that present a valid service ticket."""
    def __init__(self, key): self.key, self.seen = key, set()

    def authenticate(self, ticket, authenticator):
        t = unseal(self.key, ticket)
        if t["exp"] < time.time(): raise ValueError("service ticket expired")
        a = unseal(unb64(t["sk"]), authenticator)
        if a["client"] != t["client"] or abs(time.time() - a["ts"]) > 60: raise ValueError("authenticator mismatch/stale")
        if (a["client"], a["ts"]) in self.seen: raise ValueError("replay detected")
        self.seen.add((a["client"], a["ts"]))
        return t["client"], seal(unb64(t["sk"]), {"ts": a["ts"] + 1})   # mutual-auth reply


# ======================================================================
# THE PIPELINE: Sender and Receiver
# ======================================================================
def sender_send(data, filename, signer_key, signer_cert, receiver_pub, path, verbose=True):
    """SENDER side. Hash -> sign -> AES-128-CBC encrypt -> RSA-OAEP wrap session key -> package."""
    digest = hashlib.sha256(data).digest()                        # Task 8  (hash BEFORE transmission)
    signature = sign_digest(signer_key, digest)                   # Task 10 (sign the hash)
    session_key, iv = os.urandom(16), os.urandom(16)              # Task A  (AES-128 session key)
    ct = cbc_encrypt(AES, session_key, iv, data)
    wrapped = receiver_pub.encrypt(session_key, OAEP)             # Task 5  (hybrid encryption)
    pkg = {"filename": filename, "cipher": "AES-128-CBC", "key_wrap": "RSA-2048-OAEP-SHA256",
           "sha256": digest.hex(), "signature": b64(signature), "wrapped_key": b64(wrapped),
           "iv": b64(iv), "ciphertext": b64(ct), "sender_cert": signer_cert.public_bytes(serialization.Encoding.PEM).decode()}
    Path(path).write_text(json.dumps(pkg, indent=2))
    if verbose:
        print(f"[Sender] SHA-256(plaintext)   : {digest.hex()}")
        print(f"[Sender] RSA-PSS signature    : {signature.hex()[:64]}... ({len(signature)} B)")
        print(f"[Sender] AES-128 session key  : {session_key.hex()}   IV: {iv.hex()}")
        print(f"[Sender] ciphertext[0:32]     : {ct[:32].hex()}...  ({len(ct):,} B)")
        print(f"[Sender] RSA-OAEP wrapped key : {wrapped.hex()[:64]}... ({len(wrapped)} B)")
        print(f"[Sender] package written      : {path}")
    return pkg


def receiver_receive(path, receiver_key, trusted_fp, out_file, verbose=True):
    """RECEIVER side. Verify cert -> unwrap key -> decrypt -> re-hash -> verify signature."""
    P = print if verbose else (lambda *a, **k: None)
    pkg = json.loads(Path(path).read_text())
    cert = x509.load_pem_x509_certificate(pkg["sender_cert"].encode())
    checks = {}

    # 1. certificate validation (Task 11)
    fp = cert_fingerprint(cert)
    checks["certificate fingerprint matches pinned value"] = (fp == trusted_fp)
    checks["certificate self-signature valid"] = cert_self_signature_ok(cert)
    checks["certificate within validity period"] = cert.not_valid_before_utc <= now_utc() <= cert.not_valid_after_utc
    P(f"[Receiver] cert subject={cert.subject.rfc4514_string()}  fingerprint={fp[:32]}...")

    # 2. unwrap session key (Task 5)
    try:
        session_key = receiver_key.decrypt(unb64(pkg["wrapped_key"]), OAEP); checks["session key unwrapped"] = True
        P(f"[Receiver] unwrapped session key : {session_key.hex()}")
    except ValueError:
        checks["session key unwrapped"] = False; session_key = None

    # 3. decrypt + hash AFTER decryption (Task 8 / 9)
    plain = b""
    if session_key:
        raw = cbc_decrypt(AES, session_key, unb64(pkg["iv"]), unb64(pkg["ciphertext"]), unpad=False)
        try:
            u = sympad.PKCS7(128).unpadder(); plain = u.update(raw) + u.finalize(); checks["padding valid"] = True
        except ValueError:
            plain = raw; checks["padding valid"] = False        # corrupted final block -> still hash what we got
    h = hashlib.sha256(plain).digest()
    P(f"[Receiver] SHA-256(decrypted)  : {h.hex()}")
    P(f"[Receiver] SHA-256 claimed      : {pkg['sha256']}")
    checks["SHA-256 after decryption == sender's hash"] = (h.hex() == pkg["sha256"])

    # 4. signature on the hash (Task 10)
    checks["RSA-PSS signature valid for decrypted data"] = verify_digest(cert.public_key(), unb64(pkg["signature"]), h)

    for k, v in checks.items(): P(f"[Receiver]   {'PASS' if v else 'FAIL'}  {k}")
    ok = all(checks.values())
    if ok: Path(out_file).write_bytes(plain)
    P(f"[Receiver] => {'ACCEPTED, file saved to ' + str(out_file) if ok else 'REJECTED, nothing delivered'}")
    return ok, checks


# ======================================================================
# Sample data
# ======================================================================
def make_sample_csv(path, rows=6000):
    types = ["NEFT", "RTGS", "UPI", "IMPS", "ATM_WITHDRAWAL", "POS", "CARD_ONLINE"]
    br = ["SURT0001", "MUMB0007", "AHMD0003", "DELH0012", "BLRU0009"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txn_id", "timestamp", "from_account", "to_account", "type", "amount_inr", "branch_ifsc", "status"])
        for i in range(rows):
            w.writerow([f"TXN{10000000 + i}",
                        f"2026-09-{random.randint(1, 28):02d} {random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
                        random.randint(10**11, 10**12 - 1), random.randint(10**11, 10**12 - 1), random.choice(types),
                        round(random.lognormvariate(7.5, 1.4), 2), random.choice(br), random.choice(["SUCCESS"] * 9 + ["FAILED"])])


# ======================================================================
# Experiments for Tasks A.2, A.3, A.4, B.6, B.7
# ======================================================================
def bitdiff(a, b):
    n = min(len(a), len(b)); d = sum(bin(x ^ y).count("1") for x, y in zip(a[:n], b[:n]))
    return d, n * 8, 100.0 * d / (n * 8)


def flip(data, bitpos):
    b = bytearray(data); b[bitpos // 8] ^= 0x80 >> (bitpos % 8); return bytes(b)


def exp_a1_both_ciphers(plain, d):
    banner("TASK A.1  AES-128-CBC and 3DES-CBC on the same file")
    ak, tk = os.urandom(16), os.urandom(24)
    iva, ivt = os.urandom(16), os.urandom(8)
    ca, ct = cbc_encrypt(AES, ak, iva, plain), cbc_encrypt(TripleDES, tk, ivt, plain)
    (d / "file.aes128.enc").write_bytes(iva + ca); (d / "file.3des.enc").write_bytes(ivt + ct)
    print(f"File size : {len(plain):,} B  (requirement >= 1 KB: {'OK' if len(plain) >= 1024 else 'SMALL - experiments will repeat the data'})")
    print(f"AES-128 key {ak.hex()}\n  IV {iva.hex()}  cipher[0:32] {ca[:32].hex()}...")
    print(f"3DES key    {tk.hex()}\n  IV {ivt.hex()}  cipher[0:32] {ct[:32].hex()}...")
    ok = cbc_decrypt(AES, ak, iva, ca) == plain and cbc_decrypt(TripleDES, tk, ivt, ct) == plain
    print("Both round-trips decrypt to the original:", ok)
    record("A.1", "AES-128 and 3DES encrypt/decrypt", ok)
    return ak, tk


def exp_a2_avalanche(plain, ak, tk):
    banner("TASK A.2  Avalanche effect (single-bit flip -> % of ciphertext bits changed)")
    sample = (plain * (1024 // max(1, len(plain)) + 1))[:1024]
    iv16, iv8 = bytes(16), bytes(8)
    base = {"AES": cbc_encrypt(AES, ak, iv16, sample), "3DES": cbc_encrypt(TripleDES, tk, iv8, sample)}
    for name, alg, key, iv in [("AES-128", AES, ak, iv16), ("3DES", TripleDES, tk, iv8)]:
        b0 = base["AES" if alg is AES else "3DES"]
        c2 = cbc_encrypt(alg, key, iv, flip(sample, 0))
        d_, n_, pct = bitdiff(b0, c2); _, _, pct16 = bitdiff(b0[:16], c2[:16])
        print(f"[plaintext bit 0 flipped] {name:8s}: {d_}/{n_} bits differ = {pct:.2f}% (whole 1 KB)  |  first 16 B: {pct16:.2f}%")

    def stats(kind, target, trials=200):
        alg, key, iv = (AES, ak, iv16) if kind == "AES" else (TripleDES, tk, iv8)
        bs, res = alg.block_size // 8, []
        for _ in range(trials):
            if target == "plaintext":
                bp = random.randrange(len(sample) * 8)
                c2 = cbc_encrypt(alg, key, iv, flip(sample, bp))
                blk = (bp // 8) // bs * bs                     # CBC: earlier blocks unaffected by design -> score the block holding the flip
                res.append(bitdiff(base[kind][blk:blk + bs], c2[blk:blk + bs])[2])
            else:
                while True:
                    bp = random.randrange(len(key) * 8)
                    if kind == "AES" or bp % 8 != 7: break     # skip 3DES parity bits (ignored by the cipher)
                c2 = cbc_encrypt(alg, flip(key, bp), iv, sample)
                res.append(bitdiff(base[kind], c2)[2])
        return statistics.mean(res), min(res), max(res)

    print(f"\n{'Algorithm':10s}{'Flipped':11s}{'Mean %':>9s}{'Min %':>9s}{'Max %':>9s}   (200 random single-bit flips, ideal ~50%)")
    good = True
    for kind in ["AES", "3DES"]:
        for tgt in ["plaintext", "key"]:
            m, lo, hi = stats(kind, tgt); good &= 40 < m < 60
            print(f"{kind:10s}{tgt:11s}{m:9.2f}{lo:9.2f}{hi:9.2f}")
    record("A.2", "Avalanche effect near 50%", good)


def exp_a3_ecb_vs_cbc(ak, d, image_path=None):
    banner("TASK A.3  ECB vs CBC on an image (pattern leakage)")
    from PIL import Image, ImageDraw, ImageFont
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    if image_path:
        img = Image.open(image_path).convert("RGB").resize((512, 512))
    else:
        img = Image.new("RGB", (512, 512), (255, 255, 255)); dr = ImageDraw.Draw(img)
        dr.rectangle([0, 0, 512, 90], fill=(0, 51, 141)); dr.ellipse([40, 130, 240, 330], fill=(220, 30, 30))
        dr.rectangle([280, 130, 470, 330], fill=(255, 190, 0)); dr.polygon([(256, 360), (60, 480), (450, 480)], fill=(0, 140, 70))
        try: fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        except Exception: fnt = ImageFont.load_default()
        dr.text((70, 22), "SECURE  BANK", fill="white", font=fnt)
    img.save(d / "image_original.png")
    raw = img.tobytes()
    ecb, cbc = ecb_encrypt(ak, raw), cbc_encrypt(AES, ak, os.urandom(16), raw, pad=False)
    Image.frombytes("RGB", img.size, ecb).save(d / "image_ECB.png"); Image.frombytes("RGB", img.size, cbc).save(d / "image_CBC.png")

    def dup(ct):
        bl = [ct[i:i + 16] for i in range(0, len(ct), 16)]; return len(bl), len(bl) - len(set(bl))
    pct = {}
    for nm, ct in [("Plain image", raw), ("AES-ECB", ecb), ("AES-CBC", cbc)]:
        t, du = dup(ct); pct[nm] = 100 * du / t
        print(f"{nm:12s}: {t} blocks of 16 B, repeated blocks = {du} ({pct[nm]:.2f}%)")
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.6))
    for a, (t, f) in zip(ax, [("Original", "image_original.png"), ("AES-128 ECB (pattern leaks)", "image_ECB.png"), ("AES-128 CBC (random-looking)", "image_CBC.png")]):
        a.imshow(Image.open(d / f)); a.set_title(t); a.axis("off")
    plt.tight_layout(); plt.savefig(d / "ecb_vs_cbc.png", dpi=130); plt.close()
    print(f"Saved {d / 'ecb_vs_cbc.png'}")
    record("A.3", "ECB leaks patterns, CBC does not", pct["AES-ECB"] > 10 and pct["AES-CBC"] < 1)


def exp_a4_timing(plain, ak, tk, d):
    banner("TASK A.4  Performance: AES-128-CBC vs 3DES-CBC (mean of 3 runs)")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    rows = []
    print(f"{'Size':>7s} | {'AES enc':>9s} {'AES dec':>9s} | {'3DES enc':>9s} {'3DES dec':>9s} | 3DES/AES enc (s)")
    for mb in [1, 5, 10]:
        blob = (plain * (mb * 2**20 // len(plain) + 1))[:mb * 2**20]
        t = {k: [] for k in ("ae", "ad", "de", "dd")}
        for _ in range(3):
            iv = os.urandom(16); s = time.perf_counter(); c = cbc_encrypt(AES, ak, iv, blob); t["ae"].append(time.perf_counter() - s)
            s = time.perf_counter(); cbc_decrypt(AES, ak, iv, c); t["ad"].append(time.perf_counter() - s)
            iv = os.urandom(8); s = time.perf_counter(); c = cbc_encrypt(TripleDES, tk, iv, blob); t["de"].append(time.perf_counter() - s)
            s = time.perf_counter(); cbc_decrypt(TripleDES, tk, iv, c); t["dd"].append(time.perf_counter() - s)
        m = {k: statistics.mean(v) for k, v in t.items()}; rows.append((mb, m["ae"], m["ad"], m["de"], m["dd"]))
        print(f"{mb:5d}MB | {m['ae']:9.4f} {m['ad']:9.4f} | {m['de']:9.4f} {m['dd']:9.4f} | {m['de'] / m['ae']:.1f}x slower")
    with open(d / "timing_results.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["size_mb", "aes_enc_s", "aes_dec_s", "3des_enc_s", "3des_dec_s"]); w.writerows(rows)
    fig, ax = plt.subplots(figsize=(7, 4)); bw = 0.2
    for i, (lab, ix) in enumerate([("AES enc", 1), ("AES dec", 2), ("3DES enc", 3), ("3DES dec", 4)]):
        ax.bar([p + i * bw for p in range(3)], [r[ix] for r in rows], bw, label=lab)
    ax.set_xticks([p + 1.5 * bw for p in range(3)]); ax.set_xticklabels(["1 MB", "5 MB", "10 MB"])
    ax.set_ylabel("Time (s)"); ax.set_title("AES-128 vs 3DES (CBC)"); ax.legend(); plt.tight_layout()
    plt.savefig(d / "timing_chart.png", dpi=130); plt.close()
    record("A.4", "Timing for 3 file sizes", len(rows) == 3)


# ---------------- Diffie-Hellman ----------------
P = int("""FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1 29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245 E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE45B3D C2007CB8 A163BF05 98DA4836 1C55D39A 69163FA8 FD24CF5F
83655D23 DCA3AD96 1C62F356 208552BB 9ED52907 7096966D 670C354E 4ABC9804 F1746C08 CA18217C 32905E46 2E36CE3B
E39E772C 180E8603 9B2783A2 EC07A28F B5C55DF0 6F4C52C9 DE2BCBF6 95581718 3995497C EA956AE5 15D22618 98FA0510
15728E5A 8AACAA68 FFFFFFFF FFFFFFFF""".replace("\n", " ").replace(" ", ""), 16)   # RFC 3526 group 14 (2048-bit MODP)
G = 2
def dh_keypair(): x = secrets.randbits(256) | 1; return x, pow(G, x, P)
def dh_kdf(secret): return hashlib.sha256(secret.to_bytes(256, "big")).digest()[:16]
def int_bytes(v): return v.to_bytes(256, "big")


def exp_b6_dh(plain):
    banner("TASK B.6  Diffie-Hellman key exchange (RFC 3526 group 14, g = 2)")
    a, A = dh_keypair(); b, B = dh_keypair()
    sA, sB = pow(B, a, P), pow(A, b, P)
    print(f"Sender   public A = g^a mod p = {hex(A)[:50]}...\nReceiver public B = g^b mod p = {hex(B)[:50]}...")
    print(f"Sender   secret   = B^a mod p = {hex(sA)[:50]}...\nReceiver secret   = A^b mod p = {hex(sB)[:50]}...")
    print("Shared secrets identical:", sA == sB)
    k = dh_kdf(sA); iv = os.urandom(16)
    print("Derived AES-128 key (SHA-256 KDF):", k.hex())
    ok = cbc_decrypt(AES, dh_kdf(sB), iv, cbc_encrypt(AES, k, iv, plain)) == plain
    print("File encrypted with DH key and decrypted by receiver:", ok)
    record("B.6", "Diffie-Hellman shared secret", sA == sB and ok)


def exp_b7_mitm(sender_key, receiver_key):
    banner("TASK B.7  Man-in-the-Middle on UNAUTHENTICATED Diffie-Hellman")
    txn = b"TXN10099999|FROM 123456789012|TO 210987654321|AMOUNT INR 25000.00|PURPOSE rent"
    print("Original message (Alice=Sender, Bob=Receiver):\n  ", txn.decode())
    a, A = dh_keypair(); b, B = dh_keypair(); m, M = dh_keypair()
    print("\n[1] Alice -> A -> Mallory intercepts and forwards M to Bob")
    print("[2] Bob   -> B -> Mallory intercepts and forwards M to Alice")
    k_alice, k_bob = dh_kdf(pow(M, a, P)), dh_kdf(pow(M, b, P))
    k_ma, k_mb = dh_kdf(pow(A, m, P)), dh_kdf(pow(B, m, P))
    print(f"Alice's key {k_alice.hex()} | Mallory-Alice key {k_ma.hex()} -> equal: {k_alice == k_ma}")
    print(f"Bob's key   {k_bob.hex()} | Mallory-Bob key   {k_mb.hex()} -> equal: {k_bob == k_mb}")
    print(f"Alice key == Bob key? {k_alice == k_bob}  (each believes they share a secret with the other)")
    iv1 = os.urandom(16); c1 = cbc_encrypt(AES, k_alice, iv1, txn)
    print("\n[3] Alice sends ciphertext:", c1.hex())
    seen = cbc_decrypt(AES, k_ma, iv1, c1)
    print("[4] Mallory decrypts (confidentiality broken):", seen.decode())
    forged = seen.replace(b"TO 210987654321", b"TO 666666666666").replace(b"25000.00", b"950000.00")
    iv2 = os.urandom(16); c2 = cbc_encrypt(AES, k_mb, iv2, forged)
    got = cbc_decrypt(AES, k_bob, iv2, c2)
    print("[5] Mallory re-encrypts a forged transfer for Bob")
    print("[6] Bob decrypts a perfectly valid ciphertext:", got.decode())
    attack_ok = got == forged and seen == txn
    print("=> Attack SUCCEEDS: DH gives no authentication, so Bob accepts the forged transfer.")

    print("\n--- MITIGATION: authenticated DH (public values are signed; keys bound to certificates) ---")
    sigA, sigB = sender_key.sign(int_bytes(A), PSS, hashes.SHA256()), receiver_key.sign(int_bytes(B), PSS, hashes.SHA256())

    def ver(pub, val, sig):
        try: pub.verify(sig, int_bytes(val), PSS, hashes.SHA256()); return True
        except InvalidSignature: return False
    mallory = new_rsa()
    r1 = ver(sender_key.public_key(), A, sigA) and ver(receiver_key.public_key(), B, sigB)
    r2 = ver(sender_key.public_key(), M, sigA)
    r3 = ver(sender_key.public_key(), M, mallory.sign(int_bytes(M), PSS, hashes.SHA256()))
    print(f"Honest exchange   : Bob verifies A -> {ver(sender_key.public_key(), A, sigA)}, Alice verifies B -> {ver(receiver_key.public_key(), B, sigB)}")
    print(f"MITM, replayed sig: Bob verifies M with Alice's old signature -> {r2}  (REJECTED)")
    print(f"MITM, own key     : Bob verifies M signed by Mallory with Alice's pinned key -> {r3}  (REJECTED)")
    print("Other defences: X.509 certificates + CA trust (TLS), pre-shared keys (IPsec), SSH host-key fingerprints, ephemeral DH for forward secrecy.")
    record("B.7", "MITM succeeds on plain DH; signed DH blocks it", attack_ok and r1 and not r2 and not r3)


# ======================================================================
# MAIN
# ======================================================================
def main():
    ap = argparse.ArgumentParser(description="End-to-end encrypted file/message exchange pipeline")
    ap.add_argument("input", nargs="?", help="file to send (any type). Default: generated banking CSV")
    ap.add_argument("--message", help="send this text instead of a file")
    ap.add_argument("--out", default="pipeline_out", help="output folder (default: pipeline_out)")
    ap.add_argument("--image", help="optional image for the ECB-vs-CBC demo (default: generated logo)")
    ap.add_argument("--skip-experiments", action="store_true", help="run only the Sender->Receiver pipeline")
    args = ap.parse_args()

    out = Path(args.out)
    S, W, R, X = out / "sender", out / "wire", out / "receiver", out / "experiments"
    for p in (S, W, R, X): p.mkdir(parents=True, exist_ok=True)
    sys.stdout = Tee(out / "pipeline_log.txt")

    # ---------------- the data to send ----------------
    if args.message:
        filename, data = "message.txt", args.message.encode()
    elif args.input:
        filename, data = Path(args.input).name, Path(args.input).read_bytes()
    else:
        filename = "bank_transactions.csv"; make_sample_csv(S / filename); data = (S / filename).read_bytes()
    (S / filename).write_bytes(data)
    banner("INPUT DATA (Sender)")
    print(f"File: {filename}   Size: {len(data):,} B ({len(data) / 1024:.1f} KB)\nSHA-256: {sha256_hex(data)}")
    try: print("Preview:", data[:120].decode().splitlines()[0][:110])
    except UnicodeDecodeError: print("Preview (hex):", data[:32].hex())

    # ---------------- identities ----------------
    banner("SETUP  Key pairs and X.509 certificate (Task 11)")
    sender_key, receiver_key = new_rsa(2048), new_rsa(2048)
    sender_cert = make_self_signed_cert(sender_key, "Bank A - Sender", "Secure Banking Demo")
    (S / "sender_private.pem").write_bytes(pem_priv(sender_key)); (R / "receiver_private.pem").write_bytes(pem_priv(receiver_key))
    (R / "receiver_public.pem").write_bytes(pem_pub(receiver_key.public_key()))
    (W / "sender_cert.pem").write_bytes(sender_cert.public_bytes(serialization.Encoding.PEM))
    print("Certificate fields:")
    print(f"  Subject            : {sender_cert.subject.rfc4514_string()}\n  Issuer             : {sender_cert.issuer.rfc4514_string()}   (issuer == subject -> self-signed)")
    print(f"  Serial             : {sender_cert.serial_number}\n  Validity           : {sender_cert.not_valid_before_utc:%Y-%m-%d} to {sender_cert.not_valid_after_utc:%Y-%m-%d}")
    print(f"  Public key         : RSA {sender_cert.public_key().key_size}-bit\n  Signature algorithm: {sender_cert.signature_algorithm_oid._name}")
    print(f"  Signature          : {sender_cert.signature.hex()[:64]}...")
    trusted_fp = cert_fingerprint(sender_cert)   # delivered to the Receiver out-of-band (phone call / pinned) - this is the trust anchor
    print(f"  SHA-256 fingerprint: {trusted_fp}\n  (Receiver pins this fingerprint out-of-band, since a self-signed cert has no CA.)")
    print("Certificate self-signature verifies:", cert_self_signature_ok(sender_cert))
    record("D.11", "X.509 self-signed certificate", cert_self_signature_ok(sender_cert))

    # ---------------- Kerberos ----------------
    banner("PHASE D  Kerberos authentication of the Sender to the Receiver's server (Task 12)")
    user, password, svc = "alice@BANKA", "correct horse battery staple", "receiver-server"
    svc_key = os.urandom(16)
    kdc, server = KDC({user: pw_key(password, user)}, {svc: svc_key}), ServiceServer(svc_key)
    print("1. Client -> AS  : AS-REQ (I am alice@BANKA)")
    as_rep, tgt = kdc.as_req(user)
    print(f"2. AS -> Client  : TGT (encrypted for TGS, {len(tgt)} B) + session key SK1 (encrypted under alice's password key)")
    try:
        sk1 = unb64(unseal(pw_key("wrong password", user), as_rep)["sk"]); print("   wrong password decrypted AS-REP?!")
        bad_pw = False
    except InvalidTag:
        bad_pw = True; print("   [negative test] wrong password cannot open the AS reply -> login fails")
    sk1 = unb64(unseal(pw_key(password, user), as_rep)["sk"])
    print("   correct password opens the AS reply -> SK1 obtained")
    print("3. Client -> TGS : TGT + authenticator{client, timestamp} sealed with SK1")
    tgs_rep, st = kdc.tgs_req(tgt, seal(sk1, {"client": user, "ts": time.time()}), svc)
    sk2 = unb64(unseal(sk1, tgs_rep)["sk"])
    print(f"4. TGS -> Client : service ticket (encrypted for {svc}, {len(st)} B) + SK2")
    print("5. Client -> Server : service ticket + authenticator sealed with SK2")
    auth = seal(sk2, {"client": user, "ts": time.time()})
    who, reply = server.authenticate(st, auth)
    print(f"6. Server        : ticket decrypted, authenticator verified -> client = {who}  ACCESS GRANTED")
    print("   mutual-auth reply (ts+1) valid:", abs(unseal(sk2, reply)["ts"] - unseal(sk2, auth)["ts"] - 1) < 1e-9)
    try: server.authenticate(st, auth); replay_blocked = False
    except ValueError as e: replay_blocked = True; print(f"   [negative test] replaying the same authenticator -> {e}")
    record("D.12", "Kerberos AS -> TGS -> server", who == user and bad_pw and replay_blocked)

    # ---------------- the real delivery ----------------
    banner("PHASES A+B+C+D  SENDER -> RECEIVER (file delivery)")
    sender_send(data, filename, sender_key, sender_cert, receiver_key.public_key(), W / "package.json")
    print()
    ok, _ = receiver_receive(W / "package.json", receiver_key, trusted_fp, R / ("received_" + filename))
    delivered = (R / ("received_" + filename)).exists() and (R / ("received_" + filename)).read_bytes() == data
    print(f"\nByte-for-byte identical to original: {delivered}")
    record("A/B", "Hybrid encryption end-to-end delivery", ok and delivered)
    record("C.8", "SHA-256 before == after decryption", ok and delivered)
    record("D.10", "RSA-PSS signature verified at Receiver", ok)

    # ---------------- tampering ----------------
    banner("TASK C.9  Tampering in transit (attacker flips ONE bit of the ciphertext)")
    pkg = json.loads((W / "package.json").read_text()); ct = bytearray(unb64(pkg["ciphertext"]))
    pos = len(ct) // 2; ct[pos] ^= 0x01
    pkg["ciphertext"] = b64(bytes(ct)); (W / "package_tampered.json").write_text(json.dumps(pkg, indent=2))
    print(f"Attacker flipped bit 0 of ciphertext byte {pos:,} -> wire/package_tampered.json\n")
    ok_t, checks_t = receiver_receive(W / "package_tampered.json", receiver_key, trusted_fp, R / "tampered_output.bin")
    record("C.9", "Tampered ciphertext detected (hash mismatch)", (not ok_t) and not checks_t["SHA-256 after decryption == sender's hash"])
    record("D.10", "Tampered data fails signature check", not checks_t["RSA-PSS signature valid for decrypted data"])

    banner("EXTRA  Impersonation: attacker sends a forged message with his OWN key + self-signed cert")
    evil_key = new_rsa(2048); evil_cert = make_self_signed_cert(evil_key, "Bank A - Sender", "Secure Banking Demo")  # same name, different key
    sender_send(b"TXN99999999,TRANSFER INR 950000 TO 666666666666", "forged.csv", evil_key, evil_cert, receiver_key.public_key(), W / "package_forged.json", verbose=False)
    ok_f, checks_f = receiver_receive(W / "package_forged.json", receiver_key, trusted_fp, R / "forged_output.bin")
    print("A perfect hash and a valid signature are not enough: the Receiver rejects because the certificate fingerprint is not the pinned one.")
    record("D.11", "Forged sender (wrong certificate) rejected", not ok_f)

    # ---------------- experiments ----------------
    if not args.skip_experiments:
        ak, tk = exp_a1_both_ciphers(data, X)
        exp_a2_avalanche(data, ak, tk)
        exp_a3_ecb_vs_cbc(ak, X, args.image)
        exp_a4_timing(data, ak, tk, X)
        exp_b6_dh(data)
        exp_b7_mitm(sender_key, receiver_key)

    # ---------------- summary ----------------
    banner("FINAL RESULT")
    for t, d, p in RESULTS: print(f"  Task {t:5s} {d:55s} {'PASSED' if p else 'FAILED'}")
    allok = all(p for _, _, p in RESULTS)
    print(f"\nOverall: {'ALL CHECKS PASSED' if allok else 'SOME CHECKS FAILED'}")
    print(f"Artefacts in ./{out}:  sender/  wire/  receiver/  experiments/  pipeline_log.txt")
    sys.stdout.f.close(); sys.stdout = sys.stdout.o
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
