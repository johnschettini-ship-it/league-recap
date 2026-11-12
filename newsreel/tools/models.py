"""Find the files of the speech checker (sherpa-onnx Whisper) in a folder: any size (tiny, base, small), int8 first."""
import pathlib, sys


def whisper(wdir):
    d = pathlib.Path(wdir)
    def pick(kind):
        for pat in (f"*-{kind}.int8.onnx", f"*-{kind}.onnx"):
            found = sorted(d.glob(pat))
            if found:
                return str(found[0])
        sys.exit(f"No Whisper {kind} file in {d}. Run setup.sh.")
    tokens = sorted(d.glob("*-tokens.txt"))
    if not tokens:
        sys.exit(f"No Whisper tokens file in {d}. Run setup.sh.")
    return pick("encoder"), pick("decoder"), str(tokens[0])
