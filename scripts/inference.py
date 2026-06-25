from __future__ import annotations

import argparse

import torch
from datasets import Audio, Dataset
from transformers import WhisperForConditionalGeneration, WhisperProcessor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="model name or fine-tuned model folder")
    parser.add_argument("audio", help="audio file path")
    parser.add_argument("--language", default="tagalog")
    args = parser.parse_args()

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
        predicted_ids = model.generate(inputs)

    text = processor.tokenizer.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    print(text)


if __name__ == "__main__":
    main()
