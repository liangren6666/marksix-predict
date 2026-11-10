import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from datetime import timedelta

from ml.calendar_issue import date_to_issue, issue_to_date
from ml.data import NUM_CLASSES
from ml.regular import WARMUP, regular_features
from ml.web_prediction import build_prediction


class WebPredictionTests(unittest.TestCase):
    def setUp(self):
        self.draws = (np.arange(WARMUP + 4)[:, None] + np.arange(7)) % NUM_CLASSES + 1

    def test_next_regular_features_match_training_features_without_future_label(self):
        known, _, _ = regular_features(self.draws[:-1, :6])
        full, _, _ = regular_features(self.draws[:, :6])
        np.testing.assert_array_equal(known[-1], full[-2])

    def test_special_candidate_skips_the_selected_regular_numbers(self):
        df = pd.DataFrame(self.draws, columns=['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'special'])
        df['issue'] = np.arange(2026001, 2026001 + len(df))
        special = {'picks': [{'num': n, 'rank': n, 'p': 1 / NUM_CLASSES} for n in range(1, NUM_CLASSES + 1)]}

        with patch('ml.web_prediction.hgb_ensemble_topk', return_value=(special, df)), \
             patch('ml.web_prediction.make_hgb') as make_model:
            scores = np.linspace(0.8, 0.1, NUM_CLASSES)
            make_model.return_value.predict_proba.return_value = np.column_stack([1 - scores, scores])
            result = build_prediction()

        self.assertEqual(result['last_draw']['issue'], df.issue.iloc[-1])
        self.assertEqual(result['regular']['picks'], list(range(1, 21)))
        self.assertEqual(result['special']['picks'], list(range(1, 21)))
        self.assertEqual(result['special']['pick'], 21)
        self.assertEqual(result['special']['ranking'][0]['num'], 1)
        self.assertEqual(result['target']['issue'], date_to_issue(issue_to_date(int(df.issue.iloc[-1])) + timedelta(days=1)))

    def _frame(self):
        df = pd.DataFrame(self.draws, columns=['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'special'])
        df['issue'] = np.arange(2026001, 2026001 + len(df))
        return df

    def _mock_regular(self, make_model):
        scores = np.linspace(0.8, 0.1, NUM_CLASSES)
        make_model.return_value.predict_proba.return_value = np.column_stack([1 - scores, scores])

    def test_later_dates_roll_forward_and_change_the_ranking(self):
        df = self._frame()
        last = issue_to_date(int(df.issue.iloc[-1]))

        def rank(draws, *_args):
            shift = int(draws[-1, -1])
            numbers = [(shift + offset - 1) % NUM_CLASSES + 1 for offset in range(NUM_CLASSES)]
            ranking = [
                {"num": int(number), "rank": index, "score": float(NUM_CLASSES - index)}
                for index, number in enumerate(numbers, start=1)
            ]
            return ranking, [dict(item) for item in ranking]

        with patch('ml.web_prediction.load_newam6hc', return_value=df), \
             patch('ml.web_prediction._prepare_models', return_value=(None, None)), \
             patch('ml.web_prediction._rank_draws', side_effect=rank):
            near = build_prediction(day=last + timedelta(days=1))
            far = build_prediction(day=last + timedelta(days=3))

        self.assertEqual(near['last_draw']['issue'], int(df.issue.iloc[-1]))
        self.assertEqual(far['last_draw']['issue'], int(df.issue.iloc[-1]))
        self.assertEqual(far['target']['date'], (last + timedelta(days=3)).isoformat())
        self.assertEqual(far['target']['issue'], date_to_issue(last + timedelta(days=3)))
        self.assertIsNone(far['actual'])
        self.assertIn('未开出', far['note'])
        self.assertNotEqual(near['regular']['picks'], far['regular']['picks'])
        self.assertNotEqual(near['special']['picks'], far['special']['picks'])
        self.assertEqual(len(far['regular']['picks']), 20)
        self.assertEqual(len(far['special']['picks']), 20)

    def test_past_date_fits_only_on_earlier_draws_and_returns_the_actual_result(self):
        df = self._frame()
        day = issue_to_date(int(df.issue.iloc[-1]))
        ranking = [{'num': n, 'rank': n, 'score': 1 / NUM_CLASSES} for n in range(1, NUM_CLASSES + 1)]
        with patch('ml.web_prediction.load_newam6hc', return_value=df), \
             patch('ml.web_prediction.special_ranking_from_history', return_value=ranking) as fitted, \
             patch('ml.web_prediction.make_hgb') as make_model:
            self._mock_regular(make_model)
            result = build_prediction(day=day)
        history = fitted.call_args.args[0]
        self.assertEqual(int(history.issue.iloc[-1]), int(df.issue.iloc[-2]))
        self.assertNotIn(int(df.issue.iloc[-1]), set(history.issue))
        self.assertEqual(result['last_draw']['issue'], int(df.issue.iloc[-2]))
        self.assertEqual(result['actual']['issue'], int(df.issue.iloc[-1]))
        self.assertEqual(result['actual']['special'], int(df.special.iloc[-1]))
        self.assertEqual(len(result['special']['picks']), 20)
        self.assertEqual(len(result['regular']['picks']), 20)
