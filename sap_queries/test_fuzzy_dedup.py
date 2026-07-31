import unittest
import pandas as pd
from fuzzy_dedup_dataflow import transform, extract_diff_parts

class TestFuzzyDeduplication(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def run_transform(self, data):
        df = pd.DataFrame(data)
        result_df = transform(df)
        return result_df.to_dict('records')

    def test_standard_typos(self):
        data = [
            {'KUNNR': 1, 'LAND1': 'US', 'NAME1': 'Apple Inc', 'STRAS': '123 Main St'},
            {'KUNNR': 2, 'LAND1': 'US', 'NAME1': 'Apple Inc.', 'STRAS': '123 Main St'},
            {'KUNNR': 3, 'LAND1': 'US', 'NAME1': 'Appel Inc', 'STRAS': '123 Main St'},
        ]
        results = self.run_transform(data)
        clusters = {r['KUNNR']: r['Cluster_ID'] for r in results}
        
        # Test Clustering
        self.assertEqual(clusters['1'], '1')
        self.assertEqual(clusters['2'], '1')
        self.assertEqual(clusters['3'], '1')
        
        # Test Diff Extraction with simple thread-safe algorithm
        node_2 = next(r for r in results if r['KUNNR'] == '2')
        # Master is "APPLE INC 123 MAIN ST"
        # Node 2 is "APPLE INC. 123 MAIN ST"
        # The uncommon part is "."
        self.assertEqual(node_2['UncommonPart'], ".")
        self.assertIn("APPLE INC", node_2['CommonPart'])

    def test_cross_country_no_match(self):
        """Tests that the LAND1 block correctly prevents cross-country matches."""
        data = [
            {'KUNNR': 1, 'LAND1': 'US', 'NAME1': 'Walmart Corp'},
            {'KUNNR': 2, 'LAND1': 'CA', 'NAME1': 'Walmart Corp'}, 
        ]
        results = self.run_transform(data)
        
        # They should be dropped entirely because there are no duplicate pairs!
        self.assertEqual(len(results), 0)

    def test_extract_diff_parts(self):
        """Direct unit test of the internal diff logic algorithm."""
        c, u = extract_diff_parts("APPLE INC", "APPEL INC")
        # Simple Thread-Safe Algorithm exactly bounds the typo in the middle!
        self.assertEqual(u, "EL") 
        self.assertEqual(c, "APP ...  INC")

    def test_completely_different_records(self):
        data = [
            {'KUNNR': 1, 'LAND1': 'US', 'NAME1': 'Apple Inc'},
            {'KUNNR': 2, 'LAND1': 'US', 'NAME1': 'Banana Corp'},
            {'KUNNR': 3, 'LAND1': 'US', 'NAME1': 'Orange LLC'},
        ]
        results = self.run_transform(data)
        
        # They are all unique, so the script should drop all of them!
        self.assertEqual(len(results), 0)

    def test_transitive_chaining(self):
        data = [
            {'KUNNR': 1, 'LAND1': 'DE', 'NAME1': 'Microsoft Corporation'},
            {'KUNNR': 2, 'LAND1': 'DE', 'NAME1': 'Microsft Corporation'}, 
            {'KUNNR': 3, 'LAND1': 'DE', 'NAME1': 'Microsft Corperation'}, 
        ]
        results = self.run_transform(data)
        clusters = {r['KUNNR']: r['Cluster_ID'] for r in results}
        
        # A matches B. B matches C. Therefore A, B, C are in Cluster 1.
        self.assertEqual(clusters['1'], '1')
        self.assertEqual(clusters['2'], '1')
        self.assertEqual(clusters['3'], '1')

if __name__ == '__main__':
    unittest.main()
