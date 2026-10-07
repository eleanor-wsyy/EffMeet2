"""Loopback-only, bounded offline FunASR server for the software bench.

Install requirements-asr.txt in .venv-asr. Model weights remain in data/models.
No microphone, diarization, streaming partials, or external audio uploads.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


async def handle(ws, infer, lock):
    from websockets.exceptions import ConnectionClosed
    try:
        async with asyncio.timeout(40):
            config = json.loads(await ws.recv())
            if (not isinstance(config, dict) or config.get("mode") != "offline"
                    or config.get("wav_format") != "pcm" or config.get("audio_fs") != 16000
                    or config.get("is_speaking") is not True
                    or not isinstance(config.get("wav_name"), str)
                    or len(config["wav_name"]) > 128):
                raise ValueError("INVALID_AUDIO_CONFIG")
            pcm = bytearray()
            async for message in ws:
                if isinstance(message, bytes):
                    if len(message) % 2 or len(pcm) + len(message) > 960000:
                        raise ValueError("INVALID_AUDIO_LENGTH")
                    pcm.extend(message)
                elif json.loads(message) == {"is_speaking": False}:
                    if not pcm:
                        raise ValueError("EMPTY_AUDIO")
                    # Fail fast rather than accumulate concurrent model requests.
                    if lock.locked():
                        raise ValueError("ASR_BUSY")
                    async with lock:
                        task = asyncio.create_task(asyncio.to_thread(infer, bytes(pcm)))
                        try:
                            text = await asyncio.shield(task)
                        except asyncio.CancelledError:
                            # Keep model access serialized even if caller times out.
                            await task
                            raise
                    await ws.send(json.dumps({"mode": "offline", "wav_name": config["wav_name"],
                        "is_final": True, "text": text}, ensure_ascii=False))
                    return
                else:
                    raise ValueError("INVALID_AUDIO_END")
    except ConnectionClosed:
        return
    except (ValueError, TimeoutError) as exc:
        await ws.close(code=1008, reason=str(exc)[:100] or "ASR_TIMEOUT")
    except Exception:
        await ws.close(code=1011, reason="ASR_INFERENCE_FAILED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=10096)
    parser.add_argument("--model", default="iic/SenseVoiceSmall", help="Official model ID or downloaded local directory")
    args = parser.parse_args()
    os.environ.setdefault("MODELSCOPE_CACHE", str(ROOT / "data/models"))
    from funasr import AutoModel
    from funasr.register import tables
    from funasr.tokenizer.sentencepiece_tokenizer import SentencepiecesTokenizer
    import sentencepiece
    import numpy as np
    from websockets.asyncio.server import serve

    class UnicodePathTokenizer(SentencepiecesTokenizer):
        def _build_sentence_piece_processor(self):
            if self.sp is None:
                # Windows native SentencePiece file API fails on Chinese paths.
                # Python reads the same official model bytes without relocating it.
                self.sp = sentencepiece.SentencePieceProcessor()
                self.sp.LoadFromSerializedProto(Path(self.bpemodel).read_bytes())

    tables.tokenizer_classes["SentencepiecesTokenizer"] = UnicodePathTokenizer
    model = AutoModel(model=args.model, device="cpu", disable_update=True,
                      trust_remote_code=False, ncpu=4)

    def infer(pcm):
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        result = model.generate(input=audio, cache={}, language="zh", use_itn=True,
                                batch_size=1, disable_pbar=True)
        text = re.sub(r"<\|[^|]*\|>", "", result[0]["text"]).strip()
        if len(text) > 2000:
            raise ValueError("ASR_TEXT_TOO_LONG")
        return text

    async def run():
        lock = asyncio.Lock()
        async with serve(lambda ws: handle(ws, infer, lock), "127.0.0.1", args.port,
                         origins=[None], max_size=65536, max_queue=4, compression=None):
            print(f"LOCAL_ASR_READY ws://127.0.0.1:{args.port} (CPU / offline / max 30s)", flush=True)
            await asyncio.Future()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
