from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import evaluate
import torch
from datasets import Audio, DatasetDict, load_dataset
from transformers import (
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    WhisperForConditionalGeneration,
    WhisperProcessor,
)


@dataclass
class DataCollatorSpeechSeq2Seq:
    processor: WhisperProcessor

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        inputs = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(inputs, return_tensors="pt")
        label_inputs = [{"input_ids": f["labels"]} for f in features]
        labels = self.processor.tokenizer.pad(label_inputs, return_tensors="pt")
        batch["labels"] = labels["input_ids"].masked_fill(
            labels.attention_mask.ne(1), -100
        )
        return batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", help="dka dataset folder")
    parser.add_argument("--model", default="openai/whisper-tiny")
    parser.add_argument("--out", default="runs/whisper-ceb")
    parser.add_argument("--steps", type=int, default=200)
    args = parser.parse_args()

    root = Path(args.dataset)
    data = DatasetDict(
        {
            "train": load_dataset("csv", data_files=str(root / "exports/hf/train.csv"))[
                "train"
            ],
            "validation": load_dataset(
                "csv", data_files=str(root / "exports/hf/dev.csv")
            )["train"],
            "test": load_dataset("csv", data_files=str(root / "exports/hf/test.csv"))[
                "train"
            ],
        }
    ).cast_column("audio", Audio(sampling_rate=16000))

    processor = WhisperProcessor.from_pretrained(
        args.model, language="Cebuano", task="transcribe"
    )
    model = WhisperForConditionalGeneration.from_pretrained(args.model)
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []

    def prepare(batch: dict[str, Any]) -> dict[str, Any]:
        audio = batch["audio"]
        batch["input_features"] = processor.feature_extractor(
            audio["array"], sampling_rate=audio["sampling_rate"]
        ).input_features[0]
        batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
        return batch

    data = data.map(prepare, remove_columns=data["train"].column_names, num_proc=1)
    wer = evaluate.load("wer")
    cer = evaluate.load("cer")

    def compute_metrics(pred: Any) -> dict[str, float]:
        labels = pred.label_ids
        labels[labels == -100] = processor.tokenizer.pad_token_id
        pred_text = processor.tokenizer.batch_decode(
            pred.predictions, skip_special_tokens=True
        )
        label_text = processor.tokenizer.batch_decode(labels, skip_special_tokens=True)
        return {
            "wer": 100 * wer.compute(predictions=pred_text, references=label_text),
            "cer": 100 * cer.compute(predictions=pred_text, references=label_text),
        }

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.out,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=1e-5,
        warmup_steps=20,
        max_steps=args.steps,
        fp16=False,
        bf16=False,
        eval_strategy="steps",
        eval_steps=50,
        save_steps=50,
        logging_steps=10,
        predict_with_generate=True,
        generation_max_length=225,
        report_to=[],
        use_mps_device=torch.backends.mps.is_available(),
    )
    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=data["train"],
        eval_dataset=data["validation"],
        data_collator=DataCollatorSpeechSeq2Seq(processor),
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )
    trainer.train()
    trainer.save_model(args.out)
    processor.save_pretrained(args.out)
    print(f"saved model to {args.out}")


if __name__ == "__main__":
    main()
