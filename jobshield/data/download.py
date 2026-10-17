"""Download the EMSCAD fake job postings dataset (CC0-1.0, Hugging Face mirror)."""
import requests

from jobshield.config import EMSCAD_FILE, EMSCAD_URL


def download(force: bool = False) -> None:
    if EMSCAD_FILE.exists() and not force:
        print(f"already downloaded: {EMSCAD_FILE}")
        return
    EMSCAD_FILE.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {EMSCAD_URL}")
    with requests.get(EMSCAD_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        tmp = EMSCAD_FILE.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.replace(EMSCAD_FILE)
    print(f"saved to {EMSCAD_FILE}")


if __name__ == "__main__":
    download()
