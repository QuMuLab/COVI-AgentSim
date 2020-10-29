import datetime
import typing

import collections
import dataclasses
import numpy as np
from covid19sim.inference.helper import conditions_to_np, encode_age, encode_sex, \
    symptoms_to_np
from covid19sim.inference.message_utils import UpdateMessage
if typing.TYPE_CHECKING:
    from covid19sim.human import Human


def get_test_results_array(human, current_timestamp):
    """Will return an encoded test result array for this user's recent history
    (starting from current_timestamp).

    Negative results will be -1, unknown results 0, and positive results 1.
    """
    results = np.zeros(human.conf.get("TRACING_N_DAYS_HISTORY"))
    for real_test_result, test_timestamp, test_delay in human.test_results:
        result_day = (current_timestamp - test_timestamp).days
        if result_day < human.conf.get("TRACING_N_DAYS_HISTORY"):
            if human.time_to_test_result is not None and result_day >= human.time_to_test_result \
                    and real_test_result is not None:
                assert real_test_result in ["positive", "negative"]
                results[result_day] = 1 if real_test_result == "positive" else -1
    return results


def make_human_as_message(
        human: "Human",
        update_messages: typing.List[UpdateMessage],
        conf: typing.Dict,
):
    """
    Creates a human dataclass from a super-ultra-way-too-heavy human object.

    The returned dataclass can more properly be serialized and sent to a remote server for
    clustering/inference. All update messages aimed at the given human found in the global
    mailbox will be popped and added to the dataclass.

    Args:
        human: the human object to convert.
        update_messages: the update messages sent to human.
        conf: YAML configuration dictionary with all relevant settings for the simulation.
    Returns:
        The nice-and-slim human dataclass object.
    """
    preexisting_conditions = conditions_to_np(human.preexisting_conditions)
    obs_preexisting_conditions = conditions_to_np(human.obs_preexisting_conditions)
    rolling_all_symptoms = symptoms_to_np(human.rolling_all_symptoms, conf)
    rolling_all_reported_symptoms = symptoms_to_np(human.rolling_all_reported_symptoms, conf)

    # TODO: we could index the global mailbox by day, it might be faster that way
    contacted_uids = [key for keys in human.contact_book.uids_by_day.values() for key in keys]
    update_messages = [m for m in update_messages if m.uid in contacted_uids]

    return HumanAsMessage(
        name=human.name,
        age=encode_age(human.age),
        sex=encode_sex(human.sex),
        obs_age=encode_age(human.obs_age),
        obs_sex=encode_sex(human.obs_sex),
        preexisting_conditions=preexisting_conditions,
        obs_preexisting_conditions=obs_preexisting_conditions,

        infectiousnesses=human.infectiousnesses,
        infection_timestamp=human.infection_timestamp,
        recovered_timestamp=human.recovered_timestamp,
        test_results=get_test_results_array(human, human.env.timestamp),
        rolling_all_symptoms=rolling_all_symptoms,
        rolling_all_reported_symptoms=rolling_all_reported_symptoms,
        incubation_days=human.incubation_days,
        recovery_days=human.recovery_days,
        viral_load_to_infectiousness_multiplier=human.viral_load_to_infectiousness_multiplier,

        update_messages=update_messages,
        carefulness=human.carefulness,
        has_app=human.has_app,
        oracle_noise_random_seed=human.rng.randint(1000)
    )


@dataclasses.dataclass
class HumanAsMessage:
    # Static fields
    name: str
    age: int
    sex: str
    obs_age: int
    obs_sex: str
    preexisting_conditions: np.array
    obs_preexisting_conditions: np.array

    # Medical fields
    infectiousnesses: typing.Iterable
    # TODO: Should be reformatted to POD timestamp
    infection_timestamp: datetime.datetime
    # TODO: Should be reformatted to POD timestamp
    recovered_timestamp: datetime.datetime
    test_results: collections.deque
    rolling_all_symptoms: np.array
    rolling_all_reported_symptoms: np.array
    incubation_days: int  # NOTE: FOR NOW, USED FOR TESTING/DEBUGGING ONLY
    recovery_days: int  # NOTE: FOR NOW, USED FOR TESTING/DEBUGGING ONLY
    viral_load_to_infectiousness_multiplier: float

    # Risk-level-related fields
    update_messages: typing.List[UpdateMessage]
    carefulness: float
    has_app: bool
    oracle_noise_random_seed: int = None
