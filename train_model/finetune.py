from autotrain.trainers.clm.params import LLMTrainingParams
from autotrain.trainers.common import monitor

"""
api 那可以直接call finetune.train(your_config)
"""


@monitor
def train(config):
    if isinstance(config, dict):
        config = LLMTrainingParams(**config)

    if config.trainer == "default":
        from autotrain.trainers.clm.train_clm_default import train as train_default

        train_default(config)

    elif config.trainer == "sft":
        from autotrain.trainers.clm.train_clm_sft import train as train_sft

        train_sft(config)

    elif config.trainer == "reward":
        from autotrain.trainers.clm.train_clm_reward import train as train_reward

        train_reward(config)

    elif config.trainer == "dpo":
        from autotrain.trainers.clm.train_clm_dpo import train as train_dpo

        train_dpo(config)

    elif config.trainer == "orpo":
        from autotrain.trainers.clm.train_clm_orpo import train as train_orpo

        train_orpo(config)
