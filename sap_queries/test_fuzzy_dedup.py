import unittest
import pandas as pd
from fuzzy_dedup_dataflow import transform

class TestFuzzyDeduplication(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def run_transform_and_get_clusters(self, data):
        df = pd.DataFrame(data)
        result_df = transform(df)
        result_dicts = result_df.to_dict('records')
        return {r['ID']: r['Cluster_ID'] for r in result_dicts}

    def test_standard_typos(self):
        data = [
            {'ID': 1, 'Col1': 'Apple', 'Col2': 'Inc', 'Col3': '123 Main St'},
            {'ID': 2, 'Col1': 'Apple', 'Col2': 'Inc.', 'Col3': '123 Main St'},
            {'ID': 3, 'Col1': 'Appel', 'Col2': 'Inc', 'Col3': '123 Main St'},
        ]
        clusters = self.run_transform_and_get_clusters(data)
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)
        self.assertEqual(clusters[3], 1)

    def test_early_typos_multi_block_recall(self):
        data = [
            {'ID': 1, 'Col1': 'Walmart', 'Col2': 'Corp', 'Col3': 'HQ'},
            {'ID': 2, 'Col1': 'Qalmart', 'Col2': 'Corp', 'Col3': 'HQ'}, 
        ]
        clusters = self.run_transform_and_get_clusters(data)
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)

    def test_completely_different_records(self):
        data = [
            {'ID': 1, 'Col1': 'Apple', 'Col2': 'Inc'},
            {'ID': 2, 'Col1': 'Banana', 'Col2': 'Corp'},
            {'ID': 3, 'Col1': 'Orange', 'Col2': 'LLC'},
        ]
        clusters = self.run_transform_and_get_clusters(data)
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 2)
        self.assertEqual(clusters[3], 3)

    def test_transitive_chaining(self):
        data = [
            {'ID': 1, 'Col1': 'Microsoft', 'Col2': 'Corporation'},
            {'ID': 2, 'Col1': 'Microsft', 'Col2': 'Corporation'}, 
            {'ID': 3, 'Col1': 'Microsft', 'Col2': 'Corperation'}, 
        ]
        clusters = self.run_transform_and_get_clusters(data)
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)
        self.assertEqual(clusters[3], 1)

    def test_missing_data(self):
        data = [
            {'ID': 1, 'Col1': 'Google', 'Col2': None, 'Col3': 'Mountain View'},
            {'ID': 2, 'Col1': 'Google', 'Col2': '', 'Col3': 'Mountain View'},
        ]
        clusters = self.run_transform_and_get_clusters(data)
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)

    def test_short_strings(self):
        data = [
            {'ID': 1, 'Col1': 'IT'},
            {'ID': 2, 'Col1': 'IT'},
            {'ID': 3, 'Col1': 'HR'},
        ]
        clusters = self.run_transform_and_get_clusters(data)
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)
        self.assertEqual(clusters[3], 3)

if __name__ == '__main__':
    unittest.main()
