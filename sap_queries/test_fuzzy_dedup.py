import unittest
import pandas as pd
from fuzzy_dedup_dataflow import transform as basic_transform
from weighted_fuzzy_dedup import transform as weighted_transform

class TestFuzzyDeduplication(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        # Run every test case against both algorithms to ensure output schema parity
        self.algorithms = [basic_transform, weighted_transform]

    def test_standard_typos(self):
        data = [
            {'KUNNR': 1, 'LAND1': 'US', 'NAME1': 'Apple Inc', 'STRAS': '123 Main St'},
            {'KUNNR': 2, 'LAND1': 'US', 'NAME1': 'Apple Inc.', 'STRAS': '123 Main St'}
        ]
        df = pd.DataFrame(data)
        
        for algo in self.algorithms:
            with self.subTest(algo=algo.__module__):
                results = algo(df).to_dict('records')
                clusters = {r['KUNNR']: r['Cluster_ID'] for r in results}
                
                # Test Clustering
                self.assertEqual(clusters['1'], '1')
                self.assertEqual(clusters['2'], '1')
                
                # Test the new Field-Level Diff Extraction
                node_2 = next(r for r in results if r['KUNNR'] == '2')
                # UncommonPart should now explicitly tag the field with the typo!
                self.assertEqual(node_2['UncommonPart'], "NAME1( -> .)")
                
                # Assert Fuzzy_Score exists and contains the | separator
                self.assertIn("Fuzzy_Score", node_2)
                self.assertIn("|", node_2['Fuzzy_Score'])
                
                # CommonPart should now separate fields with the | pipe
                self.assertIn("APPLE INC", node_2['CommonPart'])
                self.assertIn("123 MAIN ST", node_2['CommonPart'])
                self.assertIn("|", node_2['CommonPart'])

    def test_cross_country_no_match(self):
        """Tests that the LAND1 block correctly prevents cross-country matches."""
        data = [
            {'KUNNR': 1, 'LAND1': 'US', 'NAME1': 'Walmart Corp'},
            {'KUNNR': 2, 'LAND1': 'CA', 'NAME1': 'Walmart Corp'}, 
        ]
        df = pd.DataFrame(data)
        for algo in self.algorithms:
            with self.subTest(algo=algo.__module__):
                results = algo(df).to_dict('records')
                # They should be dropped entirely because there are no duplicate pairs!
                self.assertEqual(len(results), 0)

    def test_completely_different_records(self):
        data = [
            {'KUNNR': 1, 'LAND1': 'US', 'NAME1': 'Apple Inc'},
            {'KUNNR': 2, 'LAND1': 'US', 'NAME1': 'Banana Corp'},
            {'KUNNR': 3, 'LAND1': 'US', 'NAME1': 'Orange LLC'},
        ]
        df = pd.DataFrame(data)
        for algo in self.algorithms:
            with self.subTest(algo=algo.__module__):
                results = algo(df).to_dict('records')
                # They are all unique, so the script should drop all of them!
                self.assertEqual(len(results), 0)

    def test_transitive_chaining(self):
        data = [
            {'KUNNR': 1, 'LAND1': 'DE', 'NAME1': 'Microsoft Corporation'},
            {'KUNNR': 2, 'LAND1': 'DE', 'NAME1': 'Microsft Corporation'}, 
            {'KUNNR': 3, 'LAND1': 'DE', 'NAME1': 'Microsft Corperation'}, 
        ]
        df = pd.DataFrame(data)
        for algo in self.algorithms:
            with self.subTest(algo=algo.__module__):
                results = algo(df).to_dict('records')
                clusters = {r['KUNNR']: r['Cluster_ID'] for r in results}
                
                # A matches B. B matches C. Therefore A, B, C are in Cluster 1.
                self.assertEqual(clusters['1'], '1')
                self.assertEqual(clusters['2'], '1')
                self.assertEqual(clusters['3'], '1')

if __name__ == '__main__':
    unittest.main()
