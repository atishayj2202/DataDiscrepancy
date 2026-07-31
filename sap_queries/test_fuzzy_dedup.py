import unittest
from fuzzy_dedup_dataflow import fuzzy_deduplicate

class TestFuzzyDeduplication(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_standard_typos(self):
        data = [
            {'ID': 1, 'Col1': 'Apple', 'Col2': 'Inc', 'Col3': '123 Main St'},
            {'ID': 2, 'Col1': 'Apple', 'Col2': 'Inc.', 'Col3': '123 Main St'},
            {'ID': 3, 'Col1': 'Appel', 'Col2': 'Inc', 'Col3': '123 Main St'}, # Late typo
        ]
        results = fuzzy_deduplicate(data)
        clusters = {r['ID']: r['Cluster_ID'] for r in results}
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)
        self.assertEqual(clusters[3], 1)

    def test_early_typos_multi_block_recall(self):
        """
        Tests if the Multi-Pass Blocking correctly catches a typo in the very first letter.
        A strict prefix-only blocker would fail this test.
        """
        data = [
            {'ID': 1, 'Col1': 'Walmart', 'Col2': 'Corp', 'Col3': 'HQ'},
            {'ID': 2, 'Col1': 'Qalmart', 'Col2': 'Corp', 'Col3': 'HQ'}, # Q instead of W
        ]
        results = fuzzy_deduplicate(data)
        clusters = {r['ID']: r['Cluster_ID'] for r in results}
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)

    def test_completely_different_records(self):
        """
        Tests that completely different records are NOT clustered.
        """
        data = [
            {'ID': 1, 'Col1': 'Apple', 'Col2': 'Inc'},
            {'ID': 2, 'Col1': 'Banana', 'Col2': 'Corp'},
            {'ID': 3, 'Col1': 'Orange', 'Col2': 'LLC'},
        ]
        results = fuzzy_deduplicate(data)
        clusters = {r['ID']: r['Cluster_ID'] for r in results}
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 2)
        self.assertEqual(clusters[3], 3)

    def test_transitive_chaining(self):
        """
        Tests if the Graph DFS correctly links A -> B -> C together into one cluster.
        """
        data = [
            {'ID': 1, 'Col1': 'Microsoft', 'Col2': 'Corporation'},
            {'ID': 2, 'Col1': 'Microsft', 'Col2': 'Corporation'}, # Matches 1
            {'ID': 3, 'Col1': 'Microsft', 'Col2': 'Corperation'}, # Matches 2, not necessarily 1 directly
        ]
        results = fuzzy_deduplicate(data)
        clusters = {r['ID']: r['Cluster_ID'] for r in results}
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)
        self.assertEqual(clusters[3], 1)

    def test_missing_data(self):
        """
        Tests if missing/None values are handled safely without crashing.
        """
        data = [
            {'ID': 1, 'Col1': 'Google', 'Col2': None, 'Col3': 'Mountain View'},
            {'ID': 2, 'Col1': 'Google', 'Col2': '', 'Col3': 'Mountain View'},
        ]
        results = fuzzy_deduplicate(data)
        clusters = {r['ID']: r['Cluster_ID'] for r in results}
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)

    def test_short_strings(self):
        """
        Tests strings that are too short to generate standard prefix/suffix blocks.
        """
        data = [
            {'ID': 1, 'Col1': 'IT'},
            {'ID': 2, 'Col1': 'IT'},
            {'ID': 3, 'Col1': 'HR'},
        ]
        results = fuzzy_deduplicate(data)
        clusters = {r['ID']: r['Cluster_ID'] for r in results}
        self.assertEqual(clusters[1], 1)
        self.assertEqual(clusters[2], 1)
        self.assertEqual(clusters[3], 3)

if __name__ == '__main__':
    unittest.main()
