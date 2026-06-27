"""
Local HF LLM using 4-bit quantization via bitsandbytes.
Loaded once at first call and kept in memory for the lifetime of the process.
"""
import logging
import threading
from collections.abc import Generator

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextIteratorStreamer,
)

from app.config import settings

logger = logging.getLogger(__name__)

_model = None
_tokenizer = None
_lock = threading.Lock()


def _load():
    global _model, _tokenizer
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        logger.info("Loading local LLM: %s (4-bit)", settings.local_llm_model)
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        _tokenizer = AutoTokenizer.from_pretrained(settings.local_llm_model)
        _model = AutoModelForCausalLM.from_pretrained(
            settings.local_llm_model,
            quantization_config=bnb,
            device_map="auto",
            torch_dtype=torch.bfloat16,
        )
        _model.eval()
        logger.info("Local LLM ready")


def stream_local(system: str, user: str) -> Generator[str, None, None]:
    _load()

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    prompt = _tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False,
    )
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)

    streamer = TextIteratorStreamer(
        _tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    gen_kwargs = dict(
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        streamer=streamer,
        max_new_tokens=settings.llm_max_tokens,
        do_sample=True,
        temperature=0.3,
        repetition_penalty=1.1,
    )

    thread = threading.Thread(target=_model.generate, kwargs=gen_kwargs)
    thread.start()

    for token in streamer:
        yield token

    thread.join()
