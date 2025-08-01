# Copyright 2023-present the HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import packaging.version
import torch
import transformers
from transformers import BloomPreTrainedModel


# needed for prefix-tuning of bloom model
def bloom_model_postprocess_past_key_value(past_key_values):
    past_key_values = torch.cat(past_key_values)
    total_layers, batch_size, num_attention_heads, num_virtual_tokens, head_dim = past_key_values.shape
    keys = past_key_values[: total_layers // 2]
    keys = keys.transpose(2, 3).reshape(
        total_layers // 2, batch_size * num_attention_heads, head_dim, num_virtual_tokens
    )
    values = past_key_values[total_layers // 2 :]
    values = values.reshape(total_layers // 2, batch_size * num_attention_heads, num_virtual_tokens, head_dim)

    return tuple(zip(keys, values))


# needed for prefix-tuning of StarCoder models
def starcoder_model_postprocess_past_key_value(past_key_values):
    result = []
    for k in past_key_values:
        k = k[:, :, 0]
        k = k.permute([1, 2, 0, 3])
        k = k.reshape(*k.shape[:-2], -1)
        result.append(k)
    return tuple(result)


# TODO: remove this once transformers 4.53 is no longer supported
TRANSFORMERS_MODELS_TO_PREFIX_TUNING_POSTPROCESS_MAPPING = {}
transformers_le_4_53 = packaging.version.parse(transformers.__version__) < packaging.version.parse("4.54.0.dev0")
if transformers_le_4_53:
    TRANSFORMERS_MODELS_TO_PREFIX_TUNING_POSTPROCESS_MAPPING["gpt_bigcode"] = (
        starcoder_model_postprocess_past_key_value
    )


if hasattr(BloomPreTrainedModel, "_convert_to_standard_cache"):
    # special handling for bloom architecture was fixed in:
    # https://github.com/huggingface/transformers/pull/31445
    # the _convert_to_standard_cache method is removed in the PR and thus serves as an indicator
    TRANSFORMERS_MODELS_TO_PREFIX_TUNING_POSTPROCESS_MAPPING["bloom"] = bloom_model_postprocess_past_key_value

TRANSFORMERS_MODELS_TO_LNTUNING_TARGET_MODULES_MAPPING = {
    "llama": ["input_layernorm", "post_attention_layernorm", "norm"],
    "bloom": ["input_layernorm", "post_attention_layernorm", "ln_f"],
    "llava": [
        "multi_modal_projector",
        "input_layernorm",
        "post_attention_layernorm",
        "norm",
        "embed_tokens",
        "lm_head",
    ],
    "t5": ["layer_norm", "final_layer_norm"],
    "mt5": ["layer_norm", "final_layer_norm"],
    "bart": ["self_attn_layer_norm", "encoder_attn_layer_norm", "final_layer_norm"],
    "gpt2": ["ln_1", "ln_2", "ln_f"],
    "blip-2": ["layernorm", "LayerNorm", "final_layer_norm", "self_attn_layer_norm"],
    "gptj": ["ln_1", "ln_f"],
    "falcon": ["input_layernorm", "post_attention_layernorm", "ln_f"],
    "mistral": ["input_layernorm", "post_attention_layernorm", "norm"],
    "phi": ["input_layernorm", "final_layernorm"],
    "gemma": ["input_layernorm", "post_attention_layernorm", "norm"],
    "gemma2": [
        "input_layernorm",
        "post_attention_layernorm",
        "pre_feedforward_layernorm",
        "post_feedforward_layernorm",
        "norm",
    ],
    "gemma3_text": [
        "input_layernorm",
        "post_attention_layernorm",
        "pre_feedforward_layernorm",
        "post_feedforward_layernorm",
        "norm",
    ],
    "qwen2": ["post_attention_layernorm"],
    "qwen3": ["post_attention_layernorm"],
}

TRANSFORMERS_MODELS_TO_LORA_TARGET_MODULES_MAPPING = {
    "t5": ["q", "v"],
    "mt5": ["q", "v"],
    "bart": ["q_proj", "v_proj"],
    "gpt2": ["c_attn"],
    "bloom": ["query_key_value"],
    "blip-2": ["q", "v", "q_proj", "v_proj"],
    "opt": ["q_proj", "v_proj"],
    "gptj": ["q_proj", "v_proj"],
    "gpt_neox": ["query_key_value"],
    "gpt_neo": ["q_proj", "v_proj"],
    "bert": ["query", "value"],
    "roberta": ["query", "value"],
    "xlm-roberta": ["query", "value"],
    "electra": ["query", "value"],
    "deberta-v2": ["query_proj", "value_proj"],
    "deberta": ["in_proj"],
    "layoutlm": ["query", "value"],
    "llama": ["q_proj", "v_proj"],
    "llama4": ["q_proj", "v_proj"],
    "chatglm": ["query_key_value"],
    "gpt_bigcode": ["c_attn"],
    "mpt": ["Wqkv"],
    "RefinedWebModel": ["query_key_value"],
    "RefinedWeb": ["query_key_value"],
    "falcon": ["query_key_value"],
    "btlm": ["c_proj", "c_attn"],
    "codegen": ["qkv_proj"],
    "mistral": ["q_proj", "v_proj"],
    "mixtral": ["q_proj", "v_proj"],
    "stablelm": ["q_proj", "v_proj"],
    "phi": ["q_proj", "v_proj", "fc1", "fc2"],
    "gemma": ["q_proj", "v_proj"],
    "gemma2": ["q_proj", "v_proj"],
    "gemma3_text": ["q_proj", "v_proj"],
    "qwen2": ["q_proj", "v_proj"],
    "qwen3": ["q_proj", "v_proj"],
}

TRANSFORMERS_MODELS_TO_LOKR_TARGET_MODULES_MAPPING = TRANSFORMERS_MODELS_TO_LORA_TARGET_MODULES_MAPPING.copy()
TRANSFORMERS_MODELS_TO_LOHA_TARGET_MODULES_MAPPING = TRANSFORMERS_MODELS_TO_LORA_TARGET_MODULES_MAPPING.copy()

TRANSFORMERS_MODELS_TO_IA3_TARGET_MODULES_MAPPING = {
    "t5": ["k", "v", "wo"],
    "mt5": ["k", "v", "wi_1"],
    "gpt2": ["c_attn", "mlp.c_proj"],
    "bloom": ["query_key_value", "mlp.dense_4h_to_h"],
    "roberta": ["key", "value", "output.dense"],
    "opt": ["q_proj", "k_proj", "fc2"],
    "gptj": ["q_proj", "v_proj", "fc_out"],
    "gpt_neox": ["query_key_value", "dense_4h_to_h"],
    "gpt_neo": ["q_proj", "v_proj", "c_proj"],
    "bart": ["q_proj", "v_proj", "fc2"],
    "gpt_bigcode": ["c_attn", "mlp.c_proj"],
    "llama": ["k_proj", "v_proj", "down_proj"],
    "llama4": ["q_proj", "v_proj", "down_proj"],
    "mistral": ["k_proj", "v_proj", "down_proj"],
    "mixtral": ["k_proj", "v_proj", "w2"],
    "bert": ["key", "value", "output.dense"],
    "deberta-v2": ["key_proj", "value_proj", "output.dense"],
    "deberta": ["in_proj", "output.dense"],
    "RefinedWebModel": ["query_key_value", "dense_4h_to_h"],
    "RefinedWeb": ["query_key_value", "dense_4h_to_h"],
    "falcon": ["query_key_value", "dense_4h_to_h"],
    "phi": ["q_proj", "v_proj", "fc2"],
    "gemma": ["q_proj", "v_proj", "down_proj"],
    "gemma2": ["q_proj", "v_proj", "down_proj"],
    "gemma3_text": ["q_proj", "v_proj", "down_proj"],
    "qwen2": ["q_proj", "v_proj", "down_proj"],
    "qwen3": ["q_proj", "v_proj", "down_proj"],
}

TRANSFORMERS_MODELS_TO_IA3_FEEDFORWARD_MODULES_MAPPING = {
    "t5": ["wo"],
    "mt5": [],
    "gpt2": ["mlp.c_proj"],
    "bloom": ["mlp.dense_4h_to_h"],
    "roberta": ["output.dense"],
    "opt": ["fc2"],
    "gptj": ["fc_out"],
    "gpt_neox": ["dense_4h_to_h"],
    "gpt_neo": ["c_proj"],
    "bart": ["fc2"],
    "gpt_bigcode": ["mlp.c_proj"],
    "llama": ["down_proj"],
    "llama4": ["down_proj"],
    "mistral": ["down_proj"],
    "mixtral": ["w2"],
    "bert": ["output.dense"],
    "deberta-v2": ["output.dense"],
    "deberta": ["output.dense"],
    "RefinedWeb": ["dense_4h_to_h"],
    "RefinedWebModel": ["dense_4h_to_h"],
    "falcon": ["dense_4h_to_h"],
    "phi": ["fc2"],
    "gemma": ["down_proj"],
    "gemma2": ["down_proj"],
    "gemma3_text": ["down_proj"],
    "qwen2": ["down_proj"],
    "qwen3": ["down_proj"],
}

TRANSFORMERS_MODELS_TO_ADALORA_TARGET_MODULES_MAPPING = {
    "t5": ["q", "k", "v", "o", "wi", "wo"],
    "mt5": ["q", "k", "v", "o", "wi_0", "wi_1", "wo"],
    "bart": ["q_proj", "k_proj", "v_proj", "out_proj", "fc1", "fc2"],
    "gpt2": ["c_attn"],
    "bloom": ["query_key_value"],
    "opt": ["q_proj", "k_proj", "v_proj", "out_proj", "fc1", "fc2"],
    "gptj": ["q_proj", "v_proj"],
    "gpt_neox": ["query_key_value"],
    "gpt_neo": ["q_proj", "v_proj"],
    "llama": ["q_proj", "v_proj"],
    "llama4": ["q_proj", "v_proj"],
    "bert": ["query", "value"],
    "roberta": ["query", "key", "value", "dense"],
    # "xlm-roberta": ["query", "value"],
    # "electra": ["query", "value"],
    "deberta-v2": ["query_proj", "key_proj", "value_proj", "dense"],
    "gpt_bigcode": ["c_attn"],
    "deberta": ["in_proj"],
    # "layoutlm": ["query", "value"],
    "gemma": ["q_proj", "v_proj"],
    "gemma2": ["q_proj", "v_proj"],
    "gemma3_text": ["q_proj", "v_proj"],
    "qwen2": ["q_proj", "v_proj"],
    "qwen3": ["q_proj", "v_proj"],
}

TRANSFORMERS_MODELS_TO_VERA_TARGET_MODULES_MAPPING = {
    "t5": ["q", "v"],
    "mt5": ["q", "v"],
    "bart": ["q_proj", "v_proj"],
    "gpt2": ["c_attn"],
    "bloom": ["query_key_value"],
    "blip-2": ["q", "v", "q_proj", "v_proj"],
    "opt": ["q_proj", "v_proj"],
    "gptj": ["q_proj", "v_proj"],
    "gpt_neox": ["query_key_value"],
    "gpt_neo": ["q_proj", "v_proj"],
    "bert": ["query", "value"],
    "roberta": ["query", "value"],
    "xlm-roberta": ["query", "value"],
    "electra": ["query", "value"],
    "deberta-v2": ["query_proj", "value_proj"],
    "deberta": ["in_proj"],
    "layoutlm": ["query", "value"],
    "llama": ["q_proj", "v_proj"],
    "llama4": ["q_proj", "v_proj"],
    "chatglm": ["query_key_value"],
    "gpt_bigcode": ["c_attn"],
    "mpt": ["Wqkv"],
    "RefinedWebModel": ["query_key_value"],
    "RefinedWeb": ["query_key_value"],
    "falcon": ["query_key_value"],
    "btlm": ["c_proj", "c_attn"],
    "codegen": ["qkv_proj"],
    "mistral": ["q_proj", "v_proj"],
    "mixtral": ["q_proj", "v_proj"],
    "stablelm": ["q_proj", "v_proj"],
    "phi": ["q_proj", "v_proj"],
    "gemma": ["q_proj", "v_proj"],
    "gemma2": ["q_proj", "v_proj"],
    "gemma3_text": ["q_proj", "v_proj"],
    "qwen2": ["q_proj", "v_proj"],
    "qwen3": ["q_proj", "v_proj"],
}

TRANSFORMERS_MODELS_TO_SHIRA_TARGET_MODULES_MAPPING = {
    "t5": ["q", "v"],
    "mt5": ["q", "v"],
    "bart": ["q_proj", "v_proj"],
    "gpt2": ["c_attn"],
    "bloom": ["query_key_value"],
    "blip-2": ["q", "v", "q_proj", "v_proj"],
    "opt": ["q_proj", "v_proj"],
    "gptj": ["q_proj", "v_proj"],
    "gpt_neox": ["query_key_value"],
    "gpt_neo": ["q_proj", "v_proj"],
    "bert": ["query", "value"],
    "roberta": ["query", "value"],
    "xlm-roberta": ["query", "value"],
    "electra": ["query", "value"],
    "deberta-v2": ["query_proj", "value_proj"],
    "deberta": ["in_proj"],
    "layoutlm": ["query", "value"],
    "llama": ["q_proj", "v_proj"],
    "chatglm": ["query_key_value"],
    "gpt_bigcode": ["c_attn"],
    "mpt": ["Wqkv"],
    "RefinedWebModel": ["query_key_value"],
    "RefinedWeb": ["query_key_value"],
    "falcon": ["query_key_value"],
    "btlm": ["c_proj", "c_attn"],
    "codegen": ["qkv_proj"],
    "mistral": ["q_proj", "v_proj"],
    "mixtral": ["q_proj", "v_proj"],
    "stablelm": ["q_proj", "v_proj"],
    "phi": ["q_proj", "v_proj"],
    "gemma": ["q_proj", "v_proj"],
    "gemma2": ["q_proj", "v_proj"],
    "gemma3_text": ["q_proj", "v_proj"],
    "qwen2": ["q_proj", "v_proj"],
}

TRANSFORMERS_MODELS_TO_FOURIERFT_TARGET_MODULES_MAPPING = {
    "t5": ["q", "v"],
    "mt5": ["q", "v"],
    "bart": ["q_proj", "v_proj"],
    "gpt2": ["mlp.c_proj"],
    "bloom": ["query_key_value"],
    "blip-2": ["q", "v", "q_proj", "v_proj"],
    "opt": ["q_proj", "v_proj"],
    "gptj": ["q_proj", "v_proj"],
    "gpt_neox": ["query_key_value"],
    "gpt_neo": ["q_proj", "v_proj"],
    "bert": ["query", "value"],
    "roberta": ["query", "value"],
    "xlm-roberta": ["query", "value"],
    "electra": ["query", "value"],
    "deberta-v2": ["query_proj", "value_proj"],
    "deberta": ["in_proj"],
    "layoutlm": ["query", "value"],
    "llama": ["q_proj", "v_proj"],
    "llama4": ["q_proj", "v_proj"],
    "chatglm": ["query_key_value"],
    "gpt_bigcode": ["mlp.c_proj"],
    "mpt": ["Wqkv"],
    "RefinedWebModel": ["query_key_value"],
    "RefinedWeb": ["query_key_value"],
    "falcon": ["query_key_value"],
    "codegen": ["qkv_proj"],
    "mistral": ["q_proj", "v_proj"],
    "mixtral": ["q_proj", "v_proj"],
    "stablelm": ["q_proj", "v_proj"],
    "phi": ["q_proj", "v_proj", "fc1", "fc2"],
    "gemma": ["q_proj", "v_proj"],
    "gemma2": ["q_proj", "v_proj"],
    "gemma3_text": ["q_proj", "v_proj"],
    "qwen2": ["q_proj", "v_proj"],
    "qwen3": ["q_proj", "v_proj"],
}

TRANSFORMERS_MODELS_TO_VBLORA_TARGET_MODULES_MAPPING = {
    "t5": ["q", "k", "v", "o", "wi", "wo"],
    "mt5": ["q", "k", "v", "o", "wi_0", "wi_1", "wo"],
    "bart": ["q_proj", "k_proj", "v_proj", "out_proj", "fc1", "fc2"],
    "gpt2": ["c_attn"],
    "bloom": ["query_key_value"],
    "opt": ["q_proj", "k_proj", "v_proj", "out_proj", "fc1", "fc2"],
    "gptj": ["q_proj", "v_proj"],
    "gpt_neox": ["query_key_value"],
    "gpt_neo": ["q_proj", "v_proj"],
    "llama": ["q_proj", "v_proj"],
    "llama4": ["q_proj", "v_proj"],
    "bert": ["query", "value"],
    "roberta": ["query", "value"],
    "deberta-v2": ["query_proj", "key_proj", "value_proj", "dense"],
    "gpt_bigcode": ["c_attn"],
    "deberta": ["in_proj"],
    "gemma": ["q_proj", "v_proj"],
    "gemma2": ["q_proj", "v_proj"],
    "gemma3_text": ["q_proj", "v_proj"],
    "qwen2": ["q_proj", "v_proj"],
    "qwen3": ["q_proj", "v_proj"],
}

TRANSFORMERS_MODELS_TO_C3A_TARGET_MODULES_MAPPING = {
    "t5": ["q", "v"],
    "mt5": ["q", "v"],
    "bart": ["q_proj", "v_proj"],
    "gpt2": ["mlp.c_proj"],
    "bloom": ["query_key_value"],
    "blip-2": ["q", "v", "q_proj", "v_proj"],
    "opt": ["q_proj", "v_proj"],
    "gptj": ["q_proj", "v_proj"],
    "gpt_neox": ["query_key_value"],
    "gpt_neo": ["q_proj", "v_proj"],
    "bert": ["query", "value"],
    "roberta": ["query", "value"],
    "xlm-roberta": ["query", "value"],
    "electra": ["query", "value"],
    "deberta-v2": ["query_proj", "value_proj"],
    "deberta": ["in_proj"],
    "layoutlm": ["query", "value"],
    "llama": ["q_proj", "v_proj"],
    "llama4": ["q_proj", "v_proj"],
    "chatglm": ["query_key_value"],
    "gpt_bigcode": ["mlp.c_proj"],
    "mpt": ["Wqkv"],
    "RefinedWebModel": ["query_key_value"],
    "RefinedWeb": ["query_key_value"],
    "falcon": ["query_key_value"],
    "codegen": ["qkv_proj"],
    "mistral": ["q_proj", "v_proj"],
    "mixtral": ["q_proj", "v_proj"],
    "stablelm": ["q_proj", "v_proj"],
    "phi": ["q_proj", "v_proj", "fc1", "fc2"],
    "gemma": ["q_proj", "v_proj"],
    "gemma2": ["q_proj", "v_proj"],
    "gemma3_text": ["q_proj", "v_proj"],
    "qwen2": ["q_proj", "v_proj"],
    "qwen3": ["q_proj", "v_proj"],
}

TRANSFORMERS_MODELS_TO_RANDLORA_TARGET_MODULES_MAPPING = (
    TRANSFORMERS_MODELS_TO_LORA_TARGET_MODULES_MAPPING  # Leaving this for now but RandLoRA is flexible
)

WEIGHTS_NAME = "adapter_model.bin"
SAFETENSORS_WEIGHTS_NAME = "adapter_model.safetensors"
CONFIG_NAME = "adapter_config.json"
EMBEDDING_LAYER_NAMES = ["embed_tokens", "lm_head"]
SEQ_CLS_HEAD_NAMES = ["score", "classifier"]
INCLUDE_LINEAR_LAYERS_SHORTHAND = "all-linear"
TOKENIZER_CONFIG_NAME = "tokenizer_config.json"
DUMMY_TARGET_MODULES = "dummy-target-modules"
DUMMY_MODEL_CONFIG = {"model_type": "custom"}

# If users specify more than this number of target modules, we apply an optimization to try to reduce the target modules
# to a minimal set of suffixes, which makes loading faster. We only apply this when exceeding a certain size since
# otherwise there is no point in optimizing and there is a small chance of bugs in the optimization algorithm, so no
# point in taking unnecessary risks. See #2045 for more context.
MIN_TARGET_MODULES_FOR_OPTIMIZATION = 20
