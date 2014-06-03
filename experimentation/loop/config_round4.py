# -*- coding: utf-8 -*-
u"""
Bootstrap Experimental evaluation round 1.

Usage:
    config_round1.py <testdata.csv> <dbname>

Options:
 -h --help              Show this screen.

The testdata.csv argument is a csv file containing the gold standard to be used
to evaluate the different configurations. The absolute path and the md5 of the
file will be added to the configurations.

"""
import os
import hashlib

from utils import apply_dict_combinations, check_configs

# Proposing as candidates here the champion of the
# experimentation/classifier/config_round3.py
# and 2 prospectives of experimentation/classifier/config_round4.py
features = [u'BagOfVerbLemmas False',
            u'BagOfVerbLemmas True',
            u'BagOfVerbStems False',
            u'BagOfVerbStems True',
            #u'bag_of_pos',
            u'bag_of_pos_in_between',
            #u'bag_of_word_bigrams',
            u'bag_of_word_bigrams_in_between',
            #u'bag_of_wordpos',
            #u'bag_of_wordpos_bigrams',
            u'bag_of_wordpos_bigrams_in_between',
            u'bag_of_wordpos_in_between',
            #u'bag_of_words',
            u'bag_of_words_in_between',
            u'entity_distance',
            u'entity_order',
            u'in_same_sentence',
            u'number_of_tokens',
            u'other_entities_in_between',
            u'symbols_in_between',
            u'total_number_of_entities',
            u'verbs_count',
            u'verbs_count_in_between']
candidate_classifiers = [
    {
        u'classifier': u'svm',
        u'classifier_args': {'gamma': 0.0001},
        u'dimensionality_reduction': None,
        u'dimensionality_reduction_dimension': None,
        u'feature_selection': None,
        u'feature_selection_dimension': None,
        u'features': features,
        u'scaler': True,
        u'sparse': False},
    {
        u'classifier': u'svm',
        u'classifier_args': {
            u'class_weight': 'auto',
            u'gamma': 0.0001,
            u'kernel': u'rbf'},
        u'dimensionality_reduction': None,
        u'dimensionality_reduction_dimension': None,
        u'features': features,
        u'feature_selection': None,
        u'feature_selection_dimension': None,
        u'scaler': True,
        u'sparse': True,
    },
    {
        u'classifier': u'svm',
        u'classifier_args': {
            u'class_weight': 'auto',
            u'degree': 4,
            u'gamma': 0.0,
            u'kernel': u'poly'},
        u'dimensionality_reduction': None,
        u'dimensionality_reduction_dimension': None,
        u'features': features,
        u'feature_selection': u'kbest',
        u'feature_selection_dimension': 100,
        u'scaler': True,
        u'sparse': True,
    }
]


def iter_configs(input_file_path, dbname):
    input_file_path = os.path.abspath(input_file_path)
    hasher = hashlib.md5(open(input_file_path, 'rb').read())
    base = {
        # Experiment configuration
        u'experiment': u'bootstrap',
        u'config_version': u'4',
        u'data_shuffle_seed': "a-ha",
        u'input_file_path': input_file_path,
        u'input_file_md5': hasher.hexdigest(),
        u'database_name': dbname,

        # Human In The Middle configuration
        u'answers_per_round': 5,
        u'max_number_of_rounds': 15,

        # Bootstrap configuration
        u'prediction_config': {
            u'method': u'decision_function',
            u'scale_to_range': [0.1, 0.9]
        },
        # threshold are expressed as delta to max, so it's uniformly expressed
        # having scaling enabled or not
        u'fact_threshold_distance': 0.01,
        u'evidence_threshold_distance': 0.01,
        u'questions_sorting': u'score',
        u'drop_guesses_each_round': True,
        u'seed_facts': {
            u'number_to_use': 5,
            u'shuffle': u"it's a trap"
        },

        # Classifier configuration
        u'classifier_config': {}  # to be filled with each candidate-classifier
    }

    prediction_patch = {
        u'method': [u'predict', u'predict_proba'],
        u'scale_to_range': [None, [0.1, 0.9]]
    }
    prediction_options_range = list(
        apply_dict_combinations(base['prediction_config'], prediction_patch)
    )
    seed_patch = {
        u'shuffle': [u"%i lemon and half lemon" % i for i in range(2)]
    }
    seed_options_range = list(
        apply_dict_combinations(base[u'seed_facts'], seed_patch)
    )

    patch = {
        u'answers_per_round': [3, 5],
        u'prediction_config': prediction_options_range,
        u'fact_threshold_distance': [0.01, 0.05, 0.1],
        u'evidence_threshold_distance': [0.05, 0.1],
        u'questions_sorting': [u'score', u'certainty'],
        u'seed_facts': seed_options_range
    }

    for classifier_config in candidate_classifiers:
        base[u'classifier_config'] = classifier_config
        for config in apply_dict_combinations(base, patch):
            # Threshold adjustments

            if config[u'fact_threshold_distance'] < config[u'evidence_threshold_distance']:
                # Based on champions of prior rounds, delta for facts shall
                # be greater than delta for evidences.
                # skipping...
                continue

            max_score = 1.0
            if config[u'prediction_config']['scale_to_range']:
                max_score = max(config[u'prediction_config']['scale_to_range'])
            config[u'fact_threshold'] = max_score - config.pop(u'fact_threshold_distance')
            config[u'evidence_threshold'] = max_score - config.pop(u'evidence_threshold_distance')
            if (config[u'classifier_config'][u'classifier'] == u'svm' and
                config[u'prediction_config'][u'method'] == u'predict_proba'):
                # For SVMs, predict_proba will be replaced with decision_function
                # http://scikit-learn.org/stable/modules/svm.html#scores-and-probabilities
                config[u'classifier_config'][u'classifier_args'][u'probability'] = False
                config[u'prediction_config'][u'method'] = u'decision_function'
                # Also, given that decision_function  with rbf doest run on sparse matrixes
                if config[u'classifier_config'][u'classifier_args'].get('kernel', '') == 'rbf':
                    config[u'classifier_config'][u'sparse'] = False
            yield config


if __name__ == '__main__':
    import json
    import sys
    import logging

    from docopt import docopt

    logging.basicConfig(level=logging.INFO)

    opts = docopt(__doc__)
    configs = list(iter_configs(opts[u'<testdata.csv>'], opts[u'<dbname>']))
    check_configs(configs, estimated_minutes_per_config=18)
    json.dump(configs, sys.stdout, sort_keys=True, indent=4,
              separators=(u',', u': '))