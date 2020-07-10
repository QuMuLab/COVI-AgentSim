import unittest

import numpy as np

from covid19sim.epidemiology.symptoms import _disease_phase_id_to_idx, _disease_phase_idx_to_id,\
    _get_allergy_progression, _get_cold_progression, _get_covid_fatigue_probability, \
    _get_covid_fever_probability, _get_covid_gastro_probability, _get_covid_progression, \
    _get_covid_sickness_severity, _get_covid_trouble_breathing_probability, \
    _get_covid_trouble_breathing_severity, _get_flu_progression, \
    SYMPTOMS, DISEASES_PHASES, \
    COVID_INCUBATION, \
    COVID_ONSET, \
    COVID_PLATEAU, \
    COVID_POST_PLATEAU_1, \
    COVID_POST_PLATEAU_2
from covid19sim.epidemiology.human_properties import _get_preexisting_conditions, PREEXISTING_CONDITIONS, \
    HEART_DISEASE_IF_SMOKER_OR_DIABETES_MODIFIER, CANCER_OR_COPD_IF_SMOKER_MODIFIER, \
    IMMUNO_SUPPRESSED_IF_CANCER_MODIFIER


class Symptoms(unittest.TestCase):
    def test_disease_phase_idx_to_id(self):
        for disease in DISEASES_PHASES:
            for phase_idx, phase_id in DISEASES_PHASES[disease].items():
                self.assertEqual(_disease_phase_idx_to_id(disease, phase_idx), phase_id)

    def test_disease_phase_id_to_idx(self):
        for disease in DISEASES_PHASES:
            for phase_idx, phase_id in DISEASES_PHASES[disease].items():
                self.assertEqual(_disease_phase_id_to_idx(disease, phase_id), phase_idx)

    def test_symptoms_structure(self):
        for s_name, s_prob in SYMPTOMS.items():
            self.assertEqual(s_name, s_prob.name)

            s_prob_diseases_phases = set(s_prob.probabilities.keys())
            if s_prob_diseases_phases:
                # At least a full set of disease_phases should be found
                # in the list of disease_phases of the symptom
                for disease_label, disease_phases in DISEASES_PHASES.items():
                    if set(disease_phases.values()).issubset(s_prob_diseases_phases):
                        break
                else:
                    self.assertTrue(False,
                                    msg=f"{s_name} symptom should contain at least "
                                    f"a full set of a disease's phases")


class AllergyProgression(unittest.TestCase):
    def test_allergy_progression(self):
        """
            Test the distribution of the allergy progression
        """
        disease_phases = DISEASES_PHASES['allergy']

        out_of_context_symptoms = set()
        for _, prob in SYMPTOMS.items():
            for disease_phase in prob.probabilities:
                if disease_phase in disease_phases.values():
                    break
            else:
                out_of_context_symptoms.add(prob.id)

        n_people = 10000

        rng = np.random.RandomState(1234)

        # To simplify the tests, we expect each stage to last 1 day
        computed_dist = [set(_get_allergy_progression(rng)[0]) for _ in range(n_people)]

        probs = [0] * len(SYMPTOMS)

        for human_symptoms in computed_dist:
            for s_name, s_prob in SYMPTOMS.items():
                probs[s_prob.id] += int(s_name in human_symptoms)

        for i in range(len(probs)):
            probs[i] /= n_people

        for s_name, s_prob in SYMPTOMS.items():
            s_id = s_prob.id

            for i, (disease_phase, expected_prob) in enumerate((c, p) for c, p in s_prob.probabilities.items()
                                                         if c in disease_phases.values()):
                prob = probs[s_id]

                self.assertAlmostEqual(prob, expected_prob,
                                       delta=0 if expected_prob in (0, 1)
                                       else max(0.015, expected_prob * 0.05),
                                       msg=f"Computation of the symptom [{s_name}] yielded an "
                                       f"unexpected probability in disease_phase {disease_phase}")

            if s_id in out_of_context_symptoms:
                prob = probs[s_id]

                self.assertEqual(prob, 0.0,
                                 msg=f"Symptom [{s_name}] should not be present is the "
                                 f"list of symptoms.")


class ColdProgression(unittest.TestCase):
    def test_cold_v2_symptoms(self):
        """
            Test the distribution of the cold symptoms
        """
        disease_phases = DISEASES_PHASES['cold']

        def _get_id(symptom):
            return SYMPTOMS[symptom].id

        out_of_context_symptoms = set()
        for _, prob in SYMPTOMS.items():
            for disease_phase in prob.probabilities:
                if disease_phase in disease_phases.values():
                    break
            else:
                out_of_context_symptoms.add(prob.id)

        n_people = 10000

        rng = np.random.RandomState(1234)

        age = 25
        carefulness = 0.50
        really_sick_options = (True, False)
        extremely_sick_options = (True, False)
        preexisting_conditions_options = (tuple(), ('pre1', 'pre2'))

        for really_sick in really_sick_options:
            for extremely_sick in extremely_sick_options if really_sick else (False,):
                for preexisting_conditions in preexisting_conditions_options:
                    # To simplify the tests, we expect each stage to last 1 day
                    computed_dist = [[day_symptoms for day_symptoms in
                                      _get_cold_progression(age, rng, carefulness, preexisting_conditions,
                                                            really_sick, extremely_sick)]
                                     for _ in range(n_people)]

                    probs = [[0] * len(SYMPTOMS) for _ in disease_phases]
                    # Number of phases occurences.
                    phases_occurrence_count = [0] * len(disease_phases)

                    for human_symptoms in computed_dist:
                        # Assert that there are no symptoms on the first day
                        for day_symptoms in human_symptoms[:1]:
                            self.assertEqual(len(day_symptoms), 0)

                        # There is a chance for the cold to lasts only 2 days,
                        # with the 'cold' phase being skipped
                        if human_symptoms[1] is human_symptoms[-1]:
                            phases = [set(), set(human_symptoms[-1])]
                        else:
                            phases = [set(human_symptoms[1]), set(human_symptoms[-1])]

                        for i, day_symptoms in enumerate(phases):
                            # There is a chance for the cold to lasts only 2 days,
                            # with the 'cold' phase being skipped
                            if i == 0 and len(day_symptoms) == 0:
                                continue

                            phases_occurrence_count[i] += 1
                            self.assertEqual(len([s for s in ('mild', 'moderate') if s in day_symptoms]), 1)

                            for s_name, s_prob in SYMPTOMS.items():
                                probs[i][s_prob.id] += int(s_name in day_symptoms)

                    self.assertEqual(phases_occurrence_count[1], n_people)
                    self.assertLess(phases_occurrence_count[0], phases_occurrence_count[1])

                    for symptoms_probs, phase_occurrence_count in zip(probs, phases_occurrence_count):
                        for i in range(len(symptoms_probs)):
                            symptoms_probs[i] /= phase_occurrence_count

                    for s_name, s_prob in SYMPTOMS.items():
                        s_id = s_prob.id

                        for i, (disease_phase, expected_prob) in enumerate((c, p) for c, p in s_prob.probabilities.items()
                                                                     if c in disease_phases.values()):
                            prob = probs[i][s_id]

                            if i == 0:
                                if really_sick or extremely_sick or any(preexisting_conditions):
                                    if s_id == _get_id('moderate'):
                                        expected_prob = 1
                                    elif s_id == _get_id('mild'):
                                        expected_prob = 0
                                elif s_id == _get_id('mild'):
                                    expected_prob = 1
                                elif s_id == _get_id('moderate'):
                                    expected_prob = 0

                            elif i == 1:
                                if s_id == _get_id('mild'):
                                    expected_prob = 1
                                elif s_id == _get_id('moderate'):
                                    expected_prob = 0

                            self.assertAlmostEqual(prob, expected_prob,
                                                   delta=0 if expected_prob in (0, 1)
                                                   else max(0.015, expected_prob * 0.05),
                                                   msg=f"Computation of the symptom [{s_name}] yielded an "
                                                   f"unexpected probability for age {age}, really_sick {really_sick}, "
                                                   f"extremely_sick {extremely_sick}, "
                                                   f"preexisting_conditions {len(preexisting_conditions)} "
                                                   f"and carefulness {carefulness} in disease_phase {disease_phase}")

                        if s_id in out_of_context_symptoms:
                            prob = sum(probs[i][s_id] for i in range(len(probs))) / len(probs)

                            self.assertEqual(prob, 0.0,
                                             msg=f"Symptom [{s_name}] should not be present is the "
                                             f"list of symptoms. age {age}, really_sick {really_sick}, "
                                             f"extremely_sick {extremely_sick}, "
                                             f"preexisting_conditions {len(preexisting_conditions)} "
                                             f"and carefulness {carefulness}")


class CovidProgression(unittest.TestCase):
    disease_phases = DISEASES_PHASES['covid']

    n_people = 10000
    initial_viral_load_options = (0.50, 0.75)  # This test only checks for 0.6 threshold
    viral_load_plateau_start = 1
    viral_load_plateau_end = 2
    viral_load_recovered = 4
    ages_options = (50,)  # This test doesn't do checks on age
    incubation_days = 1
    infectiousness_onset_days = 1
    really_sick_options = (True, False)
    extremely_sick_options = (True, False)
    preexisting_conditions_options = (tuple(), ('pre1', 'pre2'), ('pre1', 'pre2', 'pre3'))
    carefulness_options = (0.50,)  # This test doesn't do checks on carefulness
    sickness_severities_options = ['mild', 'moderate', 'severe', 'extremely-severe']

    def setUp(self):
        self.out_of_context_symptoms = set()
        for _, prob in SYMPTOMS.items():
            for disease_phase in prob.probabilities:
                if disease_phase in self.disease_phases.values():
                    break
            else:
                self.out_of_context_symptoms.add(prob.id)

    @staticmethod
    def _get_id(symptom):
        return SYMPTOMS[symptom].id

    @staticmethod
    def _get_probability(symptom_probs, disease_phase_id):
        if isinstance(symptom_probs, str):
            symptom_probs = SYMPTOMS[symptom_probs]
        return symptom_probs.probabilities[disease_phase_id]

    def test_covid_sickness_severity(self):
        _get_id = self._get_id
        rng = np.random.RandomState(1234)

        disease_phases = self.disease_phases

        for initial_viral_load in self.initial_viral_load_options:
            for really_sick in self.really_sick_options:
                for extremely_sick in self.extremely_sick_options if really_sick else (False,):
                    for preexisting_conditions in self.preexisting_conditions_options:
                        for phase_id in disease_phases.values():
                            computed_severities = [_get_covid_sickness_severity(
                                rng, phase_id, really_sick, extremely_sick,
                                list(preexisting_conditions), initial_viral_load)
                                for _ in range(self.n_people)]

                            probs = [0] * len(self.sickness_severities_options)

                            for severity in computed_severities:
                                if phase_id == COVID_INCUBATION:
                                    self.assertIs(severity, None)
                                    continue

                                severity_id = _get_id(severity)
                                if severity_id == _get_id('mild'):
                                    probs[0] += 1
                                elif severity_id == _get_id('moderate'):
                                    probs[1] += 1
                                elif severity_id == _get_id('severe'):
                                    probs[2] += 1
                                elif severity_id == _get_id('extremely-severe'):
                                    probs[3] += 1

                            for i in range(len(probs)):
                                probs[i] /= self.n_people

                            expected_probs = [0] * len(self.sickness_severities_options)

                            # covid_onset
                            if phase_id == COVID_ONSET:
                                if really_sick or extremely_sick or len(preexisting_conditions) > 2 \
                                        or initial_viral_load > 0.6:
                                    # extremely-severe
                                    expected_probs[3] = 0
                                    # severe
                                    expected_probs[2] = 0
                                    # moderate
                                    expected_probs[1] = 1
                                    # mild
                                    expected_probs[0] = 0
                                else:
                                    # extremely-severe
                                    expected_probs[3] = 0
                                    # severe
                                    expected_probs[2] = 0
                                    # moderate
                                    expected_probs[1] = 0
                                    # mild
                                    expected_probs[0] = 1

                            # covid_plateau
                            elif phase_id == COVID_PLATEAU:
                                if extremely_sick:
                                    # extremely-severe
                                    expected_probs[3] = 1
                                    # severe
                                    expected_probs[2] = 0
                                    # moderate
                                    expected_probs[1] = 0
                                    # mild
                                    expected_probs[0] = 0
                                elif really_sick or len(preexisting_conditions) > 2 or initial_viral_load > 0.6:
                                    # extremely-severe
                                    expected_probs[3] = 0
                                    # severe
                                    expected_probs[2] = 1
                                    # moderate
                                    expected_probs[1] = 0
                                    # mild
                                    expected_probs[0] = 0
                                else:
                                    # extremely-severe
                                    expected_probs[3] = 0
                                    # severe
                                    expected_probs[2] = 0
                                    # moderate
                                    expected_probs[1] = initial_viral_load - .15
                                    # mild
                                    expected_probs[0] = 1 - (initial_viral_load - .15)

                            # covid_post_plateau_1
                            elif phase_id == COVID_POST_PLATEAU_1:
                                if extremely_sick:
                                    # extremely-severe
                                    expected_probs[3] = 0
                                    # severe
                                    expected_probs[2] = 1
                                    # moderate
                                    expected_probs[1] = 0
                                    # mild
                                    expected_probs[0] = 0
                                elif really_sick:
                                    # extremely-severe
                                    expected_probs[3] = 0
                                    # severe
                                    expected_probs[2] = 0
                                    # moderate
                                    expected_probs[1] = 1
                                    # mild
                                    expected_probs[0] = 0
                                else:
                                    # extremely-severe
                                    expected_probs[3] = 0
                                    # severe
                                    expected_probs[2] = 0
                                    # moderate
                                    expected_probs[1] = 0
                                    # mild
                                    expected_probs[0] = 1

                            # covid_post_plateau_2
                            elif phase_id == COVID_POST_PLATEAU_2:
                                if extremely_sick:
                                    # extremely-severe
                                    expected_probs[3] = 0
                                    # severe
                                    expected_probs[2] = 0
                                    # moderate
                                    expected_probs[1] = 1
                                    # mild
                                    expected_probs[0] = 0
                                else:
                                    # extremely-severe
                                    expected_probs[3] = 0
                                    # severe
                                    expected_probs[2] = 0
                                    # moderate
                                    expected_probs[1] = 0
                                    # mild
                                    expected_probs[0] = 1

                            for prob, expected_prob in zip(probs, expected_probs):
                                if expected_prob in (0, 1):
                                    delta = 0
                                else:
                                    delta = 0.1
                                self.assertAlmostEqual(prob, expected_prob, delta=delta)

    def test_covid_trouble_breathing_severity(self):
        symptoms_list_options = [[''], ['trouble_breathing']]

        for sickness_severity in self.sickness_severities_options:
            for symptoms_list in symptoms_list_options:
                computed_severity = _get_covid_trouble_breathing_severity(sickness_severity, symptoms_list)

                if 'trouble_breathing' not in symptoms_list:
                    self.assertIs(computed_severity, None)

                elif sickness_severity == 'mild':
                    self.assertEqual(computed_severity, 'light_trouble_breathing')
                elif sickness_severity == 'moderate':
                    self.assertEqual(computed_severity, 'moderate_trouble_breathing')
                elif sickness_severity in ('severe', 'extremely-severe'):
                    self.assertEqual(computed_severity, 'heavy_trouble_breathing')
                else:
                    raise ValueError(f"Invalid severity [{computed_severity}]")

    def test_covid_fever_probability(self):
        disease_phases = self.disease_phases

        for initial_viral_load in self.initial_viral_load_options:
            for really_sick in self.really_sick_options:
                for extremely_sick in self.extremely_sick_options if really_sick else (False,):
                    for preexisting_conditions in self.preexisting_conditions_options:
                        for phase_id in disease_phases.values():
                            prob = _get_covid_fever_probability(phase_id, really_sick, extremely_sick,
                                                                list(preexisting_conditions), initial_viral_load)

                            expected_prob = SYMPTOMS['fever'].probabilities[phase_id]

                            # covid_onset
                            if phase_id == COVID_ONSET:
                                if really_sick or extremely_sick or \
                                        len(preexisting_conditions) > 2 or \
                                        initial_viral_load > 0.6:
                                    expected_prob *= 2.

                            # covid_plateau
                            elif phase_id == COVID_PLATEAU:
                                if initial_viral_load > 0.6:
                                    expected_prob = 1.

                            self.assertEqual(prob, expected_prob)

    def test_covid_gastro_probability(self):
        disease_phases = self.disease_phases

        for initial_viral_load in self.initial_viral_load_options:
            for phase_id in disease_phases.values():
                prob = _get_covid_gastro_probability(phase_id, initial_viral_load)

                expected_prob = initial_viral_load - 0.15

                # covid_onset phase
                if phase_id == COVID_ONSET:
                    pass
                # covid_plateau phase
                elif phase_id == COVID_PLATEAU:
                    expected_prob *= 0.25
                # covid_post_plateau_1 phase
                elif phase_id == COVID_POST_PLATEAU_1:
                    expected_prob *= 0.1
                # covid_post_plateau_2 phase
                elif phase_id == COVID_POST_PLATEAU_2:
                    expected_prob *= 0.1
                else:
                    expected_prob = 0.

                self.assertEqual(prob, expected_prob)

    def test_covid_fatigue_probability(self):
        disease_phases = self.disease_phases

        for initial_viral_load in self.initial_viral_load_options:
            for age in self.ages_options:
                for carefulness in self.carefulness_options:
                    for phase_id in disease_phases.values():
                        prob = _get_covid_fatigue_probability(
                            phase_id, age, initial_viral_load, carefulness)

                        expected_prob = age / 200 + initial_viral_load * 0.6 - carefulness / 2

                        # covid_onset phase
                        if phase_id == COVID_ONSET:
                            pass
                        # covid_plateau phase
                        elif phase_id == COVID_PLATEAU:
                            expected_prob = expected_prob + initial_viral_load - 0.15
                        # covid_post_plateau_1 phase
                        elif phase_id == COVID_POST_PLATEAU_1:
                            expected_prob = expected_prob * 1.5 + initial_viral_load - 0.15
                        # covid_post_plateau_2 phase
                        elif phase_id == COVID_POST_PLATEAU_2:
                            expected_prob = expected_prob * 2. + initial_viral_load - 0.15
                        else:
                            expected_prob = 0.

                        # TODO: Make sure that it ok to have a expected_prob >= to 1.
                        expected_prob = min(expected_prob, 1.0)

                        self.assertEqual(prob, expected_prob)

    def test_covid_trouble_breathing_probability(self):
        disease_phases = self.disease_phases

        preexisting_conditions_options = [[], ['smoker'], ['lung_disease'], ['smoker', 'lung_disease']]

        for initial_viral_load in self.initial_viral_load_options:
            for age in self.ages_options:
                for preexisting_conditions in preexisting_conditions_options:
                    for carefulness in self.carefulness_options:
                        for phase_id in disease_phases.values():
                            prob = _get_covid_trouble_breathing_probability(
                                phase_id, age, initial_viral_load, carefulness,
                                list(preexisting_conditions))

                            expected_prob = 0.

                            # covid_onset phase
                            if phase_id == COVID_ONSET:
                                expected_prob = 0.5 * initial_viral_load - carefulness * 0.25
                            # covid_plateau phase
                            elif phase_id == COVID_PLATEAU:
                                expected_prob = 2 * (initial_viral_load - carefulness * 0.25)
                            # covid_post_plateau_1 phase
                            elif phase_id == COVID_POST_PLATEAU_1:
                                expected_prob = initial_viral_load - carefulness * 0.25
                            # covid_post_plateau_2 phase
                            elif phase_id == COVID_POST_PLATEAU_2:
                                expected_prob = 0.5 * (initial_viral_load - carefulness * 0.25)

                            if 'smoker' in preexisting_conditions or 'lung_disease' in preexisting_conditions:
                                expected_prob = (expected_prob * 4.) + age / 200

                            # TODO: Make sure that it ok to have a expected_prob >= to 1.
                            expected_prob = min(expected_prob, 1.0)

                            self.assertEqual(prob, expected_prob)

    def test_covid_progression(self):
        """
            Test the distribution of the covid symptoms
        """
        rng = np.random.RandomState(1234)

        for initial_viral_load in self.initial_viral_load_options:
            for age in self.ages_options:
                for really_sick in self.really_sick_options:
                    for extremely_sick in self.extremely_sick_options if really_sick else (False,):
                        for preexisting_conditions in self.preexisting_conditions_options:
                            for carefulness in self.carefulness_options:
                                self._test_covid_progression(
                                    rng, initial_viral_load, age, really_sick,
                                    extremely_sick, preexisting_conditions,
                                    carefulness)

    def _test_covid_progression(self, rng, initial_viral_load, age, really_sick,
                                extremely_sick, preexisting_conditions,
                                carefulness):
        _get_id = self._get_id
        _get_probability = self._get_probability
        disease_phases = self.disease_phases

        # List of list of set of symptoms (str). Each set contains the list of symptoms in a day
        computed_dist = [[set(day_symptoms) for day_symptoms in
                          _get_covid_progression(initial_viral_load, self.viral_load_plateau_start,
                                                 self.viral_load_plateau_end, self.viral_load_recovered,
                                                 age, self.incubation_days, self.infectiousness_onset_days,
                                                 really_sick, extremely_sick, rng, preexisting_conditions,
                                                 carefulness)]
                         for _ in range(self.n_people)]

        probs = [[0] * len(SYMPTOMS) for _ in disease_phases]

        for human_symptoms in computed_dist:
            # To simplify the tests, we expect each stage to last 1 day
            self.assertEqual(len(human_symptoms), len(disease_phases))

            # The covid incubation period should not have any symptoms
            for day_symptoms in human_symptoms[:self.incubation_days]:
                self.assertEqual(len(day_symptoms), 0)

            # The covid incubation period should not have any symptoms
            for i, day_symptoms in enumerate(human_symptoms[self.incubation_days:]):
                # There should be exactly 1 occurrence of any of the sickness level
                self.assertEqual(len([s for s in ('mild', 'moderate', 'severe', 'extremely-severe')
                                      if s in day_symptoms]), 1)
                if 'trouble_breathing' in day_symptoms:
                    # There should be exactly 1 occurrence of any of the trouble_breathing level
                    self.assertEqual(
                        len([s for s in ('light_trouble_breathing', 'moderate_trouble_breathing',
                                         'heavy_trouble_breathing')
                             if s in day_symptoms]),
                        1
                    )
                else:
                    # There should be no occurrence of any of the trouble_breathing level
                    self.assertEqual(
                        len([s for s in ('light_trouble_breathing', 'moderate_trouble_breathing',
                                         'heavy_trouble_breathing')
                             if s in day_symptoms]),
                        0
                    )

                for s_name, s_prob in SYMPTOMS.items():
                    # probs[0] are the probability for the incubation period
                    probs[i+1][s_prob.id] += int(s_name in day_symptoms)

        for symptoms_probs in probs:
            for i in range(len(symptoms_probs)):
                symptoms_probs[i] /= self.n_people

        for s_name, s_prob in SYMPTOMS.items():
            s_id = s_prob.id

            if s_id in {  # Sickness severities tested in test_covid_sickness_severity()
                        _get_id('mild'), _get_id('moderate'), _get_id('severe'),
                        _get_id('extremely-severe'),

                        _get_id('unusual'),

                        # Trouble breathing severities tested in test_covid_trouble_breathing_severity()
                        _get_id('light_trouble_breathing'), _get_id('moderate_trouble_breathing'),
                        _get_id('heavy_trouble_breathing')}:
                # Skip this test as maintaining of the tests would be
                # as complex as maintaining the code
                continue

            for i, (disease_phase, expected_prob) in enumerate((d_p, p) for d_p, p in s_prob.probabilities.items()
                                                               if d_p in disease_phases.values()):
                prob = probs[i][s_id]

                phase_id = _disease_phase_idx_to_id('covid', i)

                if s_id in (_get_id('fever'), _get_id('chills')):
                    fever_prob = _get_covid_fever_probability(phase_id, really_sick, extremely_sick,
                                                              list(preexisting_conditions), initial_viral_load)

                    # covid_onset
                    if phase_id == COVID_ONSET:
                        if s_id == _get_id('chills') and not extremely_sick:
                            expected_prob = 0

                    if s_id == _get_id('fever'):
                        expected_prob = fever_prob
                    else:
                        # Other symptoms are dependent on fever
                        expected_prob *= fever_prob

                if s_id in (_get_id('gastro'), _get_id('diarrhea'), _get_id('nausea_vomiting')):
                    gastro_prob = _get_covid_gastro_probability(phase_id, initial_viral_load)
                    # covid_onset
                    if phase_id == COVID_ONSET:
                        gastro_prob += _get_covid_gastro_probability(COVID_INCUBATION, initial_viral_load)

                    # covid_plateau
                    elif phase_id == COVID_PLATEAU:
                        gastro_prob += _get_covid_gastro_probability(COVID_ONSET, initial_viral_load) + \
                                       _get_covid_gastro_probability(COVID_INCUBATION, initial_viral_load)

                    # covid_post_plateau_1
                    elif phase_id == COVID_POST_PLATEAU_1:
                        gastro_prob += _get_covid_gastro_probability(COVID_PLATEAU, initial_viral_load) + \
                                       _get_covid_gastro_probability(COVID_ONSET, initial_viral_load) + \
                                       _get_covid_gastro_probability(COVID_INCUBATION, initial_viral_load)

                    # covid_post_plateau_2
                    elif phase_id == COVID_POST_PLATEAU_2:
                        gastro_prob += _get_covid_gastro_probability(COVID_POST_PLATEAU_1, initial_viral_load) + \
                                       _get_covid_gastro_probability(COVID_PLATEAU, initial_viral_load) + \
                                       _get_covid_gastro_probability(COVID_ONSET, initial_viral_load) + \
                                       _get_covid_gastro_probability(COVID_INCUBATION, initial_viral_load)

                    if s_id == _get_id('gastro'):
                        expected_prob = gastro_prob
                    else:
                        # Other symptoms are dependent on gastro
                        expected_prob *= gastro_prob

                if s_id in (_get_id('fatigue'),
                            _get_id('headache'), _get_id('confused'), _get_id('hard_time_waking_up'),
                            _get_id('lost_consciousness')):
                    fatigue_prob = _get_covid_fatigue_probability(phase_id, age, initial_viral_load, carefulness)
                    # TODO: Make sure that it ok to have a fatigue_prob >= to 1.
                    fatigue_prob = min(fatigue_prob, 1.0)

                    if s_id == _get_id('lost_consciousness') and \
                            not (really_sick or extremely_sick or len(preexisting_conditions) > 2):
                        expected_prob = 0

                    if s_id == _get_id('fatigue'):
                        expected_prob = fatigue_prob
                    else:
                        # Other symptoms are dependent on fatigue
                        expected_prob *= fatigue_prob

                if s_id in (_get_id('trouble_breathing'),
                            _get_id('sneezing'), _get_id('cough'), _get_id('runny_nose'),
                            _get_id('sore_throat'), _get_id('severe_chest_pain')):
                    trouble_breathing_prob = _get_covid_trouble_breathing_probability(
                        phase_id, age, initial_viral_load, carefulness,
                        preexisting_conditions)
                    # TODO: Make sure that it ok to have a trouble_breathing_prob >= to 1.
                    trouble_breathing_prob = min(trouble_breathing_prob, 1.0)

                    if s_id == _get_id('severe_chest_pain') and not extremely_sick:
                        expected_prob = 0

                    if s_id == _get_id('trouble_breathing'):
                        expected_prob = trouble_breathing_prob
                    else:
                        # Other symptoms are dependent on trouble_breathing
                        expected_prob *= trouble_breathing_prob

                if s_id == _get_id('loss_of_taste'):
                    # covid_onset
                    if phase_id == COVID_ONSET:
                        expected_prob += _get_probability('loss_of_taste', COVID_INCUBATION)

                    # covid_plateau
                    elif phase_id == COVID_PLATEAU:
                        expected_prob += _get_probability('loss_of_taste', COVID_ONSET) + \
                                         _get_probability('loss_of_taste', COVID_INCUBATION)

                self.assertAlmostEqual(
                    prob, expected_prob,
                    delta=0 if expected_prob in (0, 1) else max(0.015, expected_prob * 0.25),
                    msg=f"Computation of the symptom [{s_name}] yielded an unexpected "
                    f"probability for initial_viral_load {initial_viral_load}, "
                    f"age {age}, really_sick {really_sick}, extremely_sick {extremely_sick}, "
                    f"preexisting_conditions {len(preexisting_conditions)} and "
                    f"carefulness {carefulness} in disease_phase {phase_id}:{disease_phase}")

            if s_id in self.out_of_context_symptoms:
                prob = sum(probs[i][s_id] for i in range(len(probs))) / len(probs)

                self.assertEqual(prob, 0.0,
                                 msg=f"Symptom [{s_name}] should not be present is the "
                                 f"list of symptoms. initial_viral_load {initial_viral_load}, "
                                 f"age {age}, really_sick {really_sick}, extremely_sick {extremely_sick}, "
                                 f"preexisting_conditions {len(preexisting_conditions)} "
                                 f"and carefulness {carefulness}")


class FluProgression(unittest.TestCase):
    def test_flu_progression(self):
        """
            Test the distribution of the flu symptoms
        """
        disease_phases = DISEASES_PHASES['flu']

        def _get_id(symptom):
            return SYMPTOMS[symptom].id

        def _get_probability(symptom_probs, disease_phase):
            if isinstance(symptom_probs, str):
                symptom_probs = SYMPTOMS[symptom_probs]
            if isinstance(disease_phase, int):
                disease_phase = disease_phases[disease_phase]
            return symptom_probs.probabilities[disease_phase]

        out_of_context_symptoms = set()
        for _, prob in SYMPTOMS.items():
            for context in prob.probabilities:
                if context in disease_phases.values():
                    break
            else:
                out_of_context_symptoms.add(prob.id)

        n_people = 10000

        rng = np.random.RandomState(1234)

        age = 25
        carefulness = 0.50
        really_sick_options = (True, False)
        extremely_sick_options = (True, False)
        preexisting_conditions_options = (tuple(), ('pre1', 'pre2'))

        AVG_FLU_DURATION = 5 # config.py /!\

        for really_sick in really_sick_options:
            for extremely_sick in extremely_sick_options if really_sick else (False,):
                for preexisting_conditions in preexisting_conditions_options:
                    # To simplify the tests, we expect each stage to last 1 day
                    computed_dist = [[day_symptoms for day_symptoms in
                                      _get_flu_progression(age, rng, carefulness, preexisting_conditions,
                                                           really_sick, extremely_sick, AVG_FLU_DURATION)]
                                     for _ in range(n_people)]

                    probs = [[0] * len(SYMPTOMS) for _ in disease_phases]
                    # Number of phases occurences.
                    phases_occurrence_count = [0] * len(disease_phases)

                    for human_symptoms in computed_dist:
                        # There is a chance that the cold'symptoms last only
                        # 1 day (so 2 days if we include the non-symptomatic day)
                        if human_symptoms[1] is human_symptoms[-1]:
                            phases = [set(human_symptoms[0]),
                                      set(),
                                      set(human_symptoms[-1])]
                        else:
                            phases = [set(human_symptoms[0]),
                                      set(human_symptoms[1]),
                                      set(human_symptoms[-1])]

                        for i, day_symptoms in enumerate(phases):
                            # There is a chance that the cold'symptoms last only
                            # 1 day, in which case the 'cold' phase is skipped
                            if i == 1 and len(day_symptoms) == 0:
                                continue

                            phases_occurrence_count[i] += 1
                            self.assertEqual(len([s for s in ('mild', 'moderate') if s in day_symptoms]), 1)

                            for s_name, s_prob in SYMPTOMS.items():
                                probs[i][s_prob.id] += int(s_name in day_symptoms)

                    self.assertEqual(phases_occurrence_count[0], n_people)
                    self.assertEqual(phases_occurrence_count[2], n_people)
                    self.assertLess(phases_occurrence_count[1], phases_occurrence_count[2])

                    for symptoms_probs, phase_occurrence_count in zip(probs, phases_occurrence_count):
                        for i in range(len(symptoms_probs)):
                            symptoms_probs[i] /= phase_occurrence_count

                    for s_name, s_prob in SYMPTOMS.items():
                        s_id = s_prob.id

                        for i, (disease_phase, expected_prob) in enumerate((d_p, p) for d_p, p in s_prob.probabilities.items()
                                                                           if d_p in disease_phases.values()):
                            prob = probs[i][s_id]

                            if i == 0:
                                if s_id == _get_id('mild'):
                                    expected_prob = 1
                                elif s_id == _get_id('moderate'):
                                    expected_prob = 0

                            elif i == 1:
                                if really_sick or extremely_sick or any(preexisting_conditions):
                                    if s_id == _get_id('moderate'):
                                        expected_prob = 1
                                    elif s_id == _get_id('mild'):
                                        expected_prob = 0
                                elif s_id == _get_id('mild'):
                                    expected_prob = 1
                                elif s_id == _get_id('moderate'):
                                    expected_prob = 0

                            elif i == 2:
                                if s_id == _get_id('mild'):
                                    expected_prob = 1
                                elif s_id == _get_id('moderate'):
                                    expected_prob = 0

                            if s_id in (_get_id('diarrhea'), _get_id('nausea_vomiting')):
                                # 'diarrhea' and 'nausea_vomiting' are dependent
                                # on the presence of gastro in the phas symptoms
                                expected_prob *= _get_probability('gastro', i)

                            self.assertAlmostEqual(prob, expected_prob,
                                                   delta=0 if expected_prob in (0, 1)
                                                   else max(0.015, expected_prob * 0.05),
                                                   msg=f"Computation of the symptom [{s_name}] yielded an "
                                                   f"unexpected probability for age {age}, really_sick {really_sick}, "
                                                   f"extremely_sick {extremely_sick}, "
                                                   f"preexisting_conditions {len(preexisting_conditions)} "
                                                   f"and carefulness {carefulness} in disease_phases {disease_phases}")

                        if s_id in out_of_context_symptoms:
                            prob = sum(probs[i][s_id] for i in range(len(probs))) / len(probs)

                            self.assertEqual(prob, 0.0,
                                             msg=f"Symptom [{s_name}] should not be present is the "
                                             f"list of symptoms. age {age}, really_sick {really_sick}, "
                                             f"extremely_sick {extremely_sick}, "
                                             f"preexisting_conditions {len(preexisting_conditions)} "
                                             f"and carefulness {carefulness}")


class PreexistingConditions(unittest.TestCase):
    def test_preexisting_conditions_struct(self):
        for c_name, c_probs in PREEXISTING_CONDITIONS.items():
            c_id = c_probs[0].id

            for c_prob in c_probs:
                self.assertEqual(c_name, c_prob.name)
                self.assertEqual(c_prob.id, c_id)

    def _test_population_conditions_dependencies(self, population_conditions):
        for conditions in population_conditions:
            try:
                self.assertLess(conditions.index('smoker'), conditions.index('heart_disease'),
                                'smoker is a dependency of heart_disease and should '
                                'appear before heart_disease in the list of conditions')
            except ValueError:
                # smoker or heart_disease not present in the list
                pass
            try:
                self.assertLess(conditions.index('diabetes'), conditions.index('heart_disease'),
                                'diabetes is a dependency of heart_disease and should '
                                'appear before heart_disease in the list of conditions')
            except ValueError:
                # diabetes or heart_disease not present in the list
                pass

            try:
                self.assertLess(conditions.index('smoker'), conditions.index('cancer'),
                                'smoker is a dependency of cancer and should '
                                'appear before cancer in the list of conditions')
            except ValueError:
                # smoker or cancer not present in the list
                pass
            try:
                self.assertLess(conditions.index('smoker'), conditions.index('COPD'),
                                'smoker is a dependency of COPD and should '
                                'appear before COPD in the list of conditions')
            except ValueError:
                # smoker or COPD not present in the list
                pass

            # With a big enough population, this test should make sure that stroke is
            # not assigned before its dependencies. The dependencies of stroke are:
            # immuno-suppressed, lung_disease, pregnant, allergies
            try:
                self.assertGreaterEqual(conditions.index('stroke'),
                                        len(conditions) - 1 - len(['immuno-suppressed', 'lung_disease',
                                                                   'pregnant', 'allergies']),
                                        'The only conditions that are not dependencies of stroke are '
                                        'immuno-suppressed, lung_disease, pregnant, allergies')
            except ValueError:
                # stroke not present in the list
                pass

            try:
                self.assertLess(conditions.index('cancer'), conditions.index('immuno-suppressed'),
                                'cancer is a dependency of immuno-suppressed and should '
                                'appear before immuno-suppressed in the list of conditions')
            except ValueError:
                # cancer or immuno-suppressed not present in the list
                pass

    def test_preexisting_conditions(self):
        """
            Test the distribution of the preexisting conditions
        """
        def _get_id(cond):
            return PREEXISTING_CONDITIONS[cond][0].id

        def _get_probability(cond_probs, age, sex):
            if isinstance(cond_probs, str):
                cond_probs = PREEXISTING_CONDITIONS[cond_probs]
            return next((c_prob.probability for c_prob in cond_probs
                         if age < c_prob.age and (c_prob.sex in ('a', sex))))

        n_people = 10000

        rng = np.random.RandomState(1234)

        for c_name, c_probs in PREEXISTING_CONDITIONS.items():
            c_id = c_probs[0].id

            # TODO: Implement test for stroke and pregnant
            if c_id in (_get_id('stroke'), _get_id('pregnant')):
                continue

            for c_prob in c_probs:
                age, sex = c_prob.age - 1, c_prob.sex
                expected_prob = c_prob.probability

                if c_id in (_get_id('cancer'), _get_id('COPD')):
                    modifer_prob = _get_probability('smoker', age, sex)
                    expected_prob = expected_prob * \
                                    (CANCER_OR_COPD_IF_SMOKER_MODIFIER * modifer_prob +
                                     (1 - modifer_prob))

                if c_id == _get_id('heart_disease'):
                    modifer_prob = _get_probability('diabetes', age, sex) + \
                                   _get_probability('smoker', age, sex)
                    expected_prob = expected_prob * \
                                    (HEART_DISEASE_IF_SMOKER_OR_DIABETES_MODIFIER * modifer_prob +
                                     (1 - modifer_prob))

                if c_id == _get_id('immuno-suppressed'):
                    modifer_prob = _get_probability('cancer', age, sex)
                    expected_prob = expected_prob * \
                                    (IMMUNO_SUPPRESSED_IF_CANCER_MODIFIER * modifer_prob +
                                     (1 - modifer_prob))

                if c_id == _get_id('lung_disease'):
                    expected_prob = _get_probability('asthma', age, sex) + \
                                    _get_probability('COPD', age, sex)

                population_conditions = [_get_preexisting_conditions(age, sex, rng) for _ in range(n_people)]

                # The conditional probability above should cover the conditions dependencies order
                # but _test_population_conditions_dependencies makes it explicit
                self._test_population_conditions_dependencies(population_conditions)

                prob = len([1 for conditions in population_conditions if c_name in conditions]) / n_people

                self.assertAlmostEqual(prob, expected_prob,
                                       delta=0 if not expected_prob else max(0.015, expected_prob * 0.05),
                                       msg=f"Computation of the preexisting conditions [{c_name}] yielded an "
                                       f"unexpected probability for age {age} and sex {sex}")
