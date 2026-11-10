import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from ml.data import load_newam6hc, temporal_split_index
from ml.features import build_feature_matrix, build_next_features, gap_vector
from ml.probability import predict_proba_49


def history(n=80):
    draws = (np.arange(n)[:, None] + np.arange(7)[None, :]) % 49 + 1
    return draws[:, -1], draws


class FeatureTests(unittest.TestCase):
    def test_next_features_equal_training_row_after_future_is_added(self):
        specials, draws = history()
        expected = build_next_features(specials, draws, 30)
        # 下一期的任意号码只提供标签，不能影响当前预测特征。
        for future in (np.arange(1, 8), np.arange(40, 47)):
            x, _ = build_feature_matrix(
                np.append(specials, future[-1]), np.vstack([draws, future]), 30
            )
            np.testing.assert_array_equal(expected, x[-1:])

    def test_latest_draw_changes_next_features(self):
        specials, draws = history()
        old = build_next_features(specials[:-1], draws[:-1], 30)
        new = build_next_features(specials, draws, 30)
        self.assertFalse(np.array_equal(old, new))
        self.assertAlmostEqual(float(new[0, 103]), specials[-1] / 49)

    def test_training_features_do_not_read_future(self):
        specials, draws = history()
        original, _ = build_feature_matrix(specials, draws, 10)
        draws[40:] = np.arange(1, 8)
        specials = draws[:, -1]
        changed, _ = build_feature_matrix(specials, draws, 10)
        np.testing.assert_array_equal(original[:31], changed[:31])

    def test_gap_is_capped_and_keeps_nearest_occurrence(self):
        # 距今恰好 cap 期的号码不能被更早的重复覆盖。
        specials = np.array([1, 1, 2, 2, 2, 3])
        gaps = gap_vector(specials, len(specials), cap=4)
        self.assertEqual(gaps[0], 1)
        self.assertEqual(gaps[1], 0.25)
        self.assertEqual(gaps[2], 0)
        self.assertTrue(np.all((gaps >= 0) & (gaps <= 1)))

    def test_history_boundaries(self):
        specials, draws = history(30)
        self.assertEqual(build_next_features(specials, draws, 30).shape, (1, 110))
        for window in (0, -1, 31):
            with self.assertRaises(ValueError):
                build_next_features(specials, draws, window)
        with self.assertRaises(ValueError):
            build_feature_matrix(specials, draws, 30)


class DataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'draws.csv'
        self.row = dict(issue=2026001, year=2026, seq=1,
                        n1=1, n2=2, n3=3, n4=4, n5=5, n6=6, special=7)

    def test_invalid_records_fail_before_training(self):
        for field, value in [('n1', 0), ('special', 50), ('special', 6),
                             ('special', 7.5), ('special', None), ('issue', 2026002),
                             ('n1', 4294967297)]:
            with self.subTest(field=field, value=value):
                pd.DataFrame([{**self.row, field: value}]).to_csv(self.path, index=False)
                with self.assertRaises(ValueError):
                    load_newam6hc(self.path)

    def test_duplicate_and_empty_csv(self):
        for rows in ([self.row, self.row], []):
            pd.DataFrame(rows, columns=self.row.keys()).to_csv(self.path, index=False)
            with self.assertRaises(ValueError):
                load_newam6hc(self.path)

    def test_valid_records_are_sorted(self):
        pd.DataFrame([{**self.row, 'issue': 2026002, 'seq': 2}, self.row]).to_csv(self.path, index=False)
        self.assertEqual(load_newam6hc(self.path).issue.tolist(), [2026001, 2026002])

    def test_split_validation(self):
        self.assertEqual(temporal_split_index(100), (70, 85))
        for args in [(2,), (100, .8, .3), (100, 0, .2), (100, .8, 0)]:
            with self.assertRaises(ValueError):
                temporal_split_index(*args)


class StubModel:
    classes_ = np.arange(49)

    def predict_proba(self, x):
        return np.full((len(x), 49), 1 / 49)


class ProbabilityTests(unittest.TestCase):
    def test_export_predicts_from_latest_history(self):
        from ml import next_reference

        specials, draws = history()
        df = pd.DataFrame(draws, columns=['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'special'])
        seen = []

        class RecordingModel(StubModel):
            def predict_proba(self, x):
                seen.append(x.copy())
                return super().predict_proba(x)

        model = RecordingModel()
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / 'logreg_special.pkl').touch()
            (folder / 'hgb_special.pkl').touch()
            with patch('pickle.load', side_effect=[{'model': model, 'window': 30, 'blend_w': .5}, model]), \
                 patch.object(next_reference, 'load_newam6hc', return_value=df):
                result, _ = next_reference.hgb_ensemble_topk(folder, topk=49)
        self.assertEqual(len(result['picks']), 49)
        for features in seen:
            np.testing.assert_array_equal(features, build_next_features(specials, draws, 30))

    def test_export_rejects_invalid_topk_before_loading_models(self):
        from ml.next_reference import hgb_ensemble_topk

        for topk in (0, -1, 50, 1.5):
            with self.assertRaises(ValueError):
                hgb_ensemble_topk(Path('unused'), topk=topk)

    def test_missing_and_reordered_classes_use_actual_number(self):
        class SparseModel:
            classes_ = np.array([48, 2])

            def predict_proba(self, x):
                return np.array([[.8, .2]])

        proba = predict_proba_49(SparseModel(), np.zeros((1, 110)))
        self.assertEqual(proba.shape, (1, 49))
        self.assertEqual(np.argmax(proba), 48)
        self.assertEqual(proba[0, 2], .2)
        self.assertEqual(proba[0, 0], 0)


class PipelineIsolationTests(unittest.TestCase):
    def test_training_and_benchmark_only_fit_prior_samples(self):
        from ml import run_train, run_benchmark

        specials, draws = history(80)
        df = pd.DataFrame(draws, columns=['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'special'])
        df['issue'] = np.arange(2026001, 2026081)
        x, y = build_feature_matrix(specials, draws, 10)
        train_end, val_end = temporal_split_index(len(y))

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            train_calls = []
            log_calls = []

            def fit(calls):
                def fake_fit(fit_x, fit_y):
                    calls.append((fit_x.copy(), fit_y.copy()))
                    return StubModel()
                return fake_fit

            with patch.object(run_train, 'load_newam6hc', return_value=df), \
                 patch.object(run_train, 'train_hgb', side_effect=fit(train_calls)), \
                 patch.object(run_train, 'train_logreg', side_effect=fit(log_calls)), \
                 patch('sys.argv', ['train', '--window', '10', '--out-dir', str(folder / 'models'),
                                    '--report', str(folder / 'reports' / 'train.json')]), \
                 contextlib.redirect_stdout(io.StringIO()):
                run_train.main()
            for calls in (train_calls, log_calls):
                self.assertEqual([len(a) for a, _ in calls], [train_end, val_end])
                for (fit_x, fit_y), end in zip(calls, (train_end, val_end)):
                    np.testing.assert_array_equal(fit_x, x[:end])
                    np.testing.assert_array_equal(fit_y, y[:end])

            calls = []
            with patch.object(run_benchmark, 'load_newam6hc', return_value=df), \
                 patch.object(run_benchmark, 'fit_hgb', side_effect=fit(calls)), \
                 patch('sys.argv', ['benchmark', '--window', '10',
                                    '--out-json', str(folder / 'bench.json'),
                                    '--out-csv', str(folder / 'csv' / 'bench.csv')]), \
                 contextlib.redirect_stdout(io.StringIO()):
                run_benchmark.main()
            self.assertEqual([len(a) for a, _ in calls], [train_end, val_end])
            report = json.loads((folder / 'bench.json').read_text(encoding='utf-8'))
            random_rows = [r for r in report['all_results'] if r['id'] == 'random']
            self.assertTrue(all(r['top1'] == round(1 / 49, 6) for r in random_rows))


if __name__ == '__main__':
    unittest.main()
