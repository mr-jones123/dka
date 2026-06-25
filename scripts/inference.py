from __future__ import annotations

import argparse
import logging

import torch
from datasets import Audio, Dataset
from transformers import WhisperForConditionalGeneration, WhisperProcessor
from transformers.utils import logging as hf_logging


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="model name or fine-tuned model folder")
    parser.add_argument("audio", help="audio file path")
    parser.add_argument("--language", default="tagalog")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.ERROR)
    if args.verbose:
        hf_logging.set_verbosity_info()
        hf_logging.enable_progress_bar()
    else:
        hf_logging.set_verbosity_error()
        hf_logging.disable_progress_bar()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    processor = WhisperProcessor.from_pretrained(
        args.model, language=args.language, task="transcribe"
    )
    model = WhisperForConditionalGeneration.from_pretrained(args.model).to(device)
    model.eval()

    data = Dataset.from_dict({"audio": [args.audio]}).cast_column(
        "audio", Audio(sampling_rate=16000)
    )
    audio = data[0]["audio"]
    inputs = processor.feature_extractor(
        audio["array"], sampling_rate=audio["sampling_rate"], return_tensors="pt"
    ).input_features.to(device)

    with torch.no_grad():
        predicted_ids = model.generate(
            inputs, language=args.language, task="transcribe"
        )

    text = processor.tokenizer.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    print(text)


if __name__ == "__main__":
    main()
