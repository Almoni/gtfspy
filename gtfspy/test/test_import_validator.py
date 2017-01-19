# reload(sys)
# -*- encoding: utf-8 -*-
import unittest
import os
from gtfspy.gtfs import GTFS
from gtfspy import import_validator as iv
import pandas as pd

class TestImportValidator(unittest.TestCase):
    def setUp(self):

        # create validator object using textfiles

        self.gtfs_source_dir = os.path.join(os.path.dirname(__file__), "test_data")
        self.G_txt = GTFS.from_directory_as_inmemory_db(["test_data", "test_data/feed_b"])
        self.validator_object_txt = iv.ImportValidator(["test_data", "test_data/feed_b"], self.G_txt)

    def test_validator_objects(self):

        self.assertIsInstance(self.validator_object_txt, iv.ImportValidator)
        self.assertEqual(len(self.validator_object_txt.gtfs_sources), 2)

    def test_txt_import(self):
        df = self.validator_object_txt.txt_reader(self.gtfs_source_dir, 'agency')
        self.assertIsInstance(df, pd.DataFrame)

    def test_source_gtfsobj_comparison(self):
        self.validator_object_txt.source_gtfsobj_comparison()

    def test_null_counts_in_gtfsobj(self):
        self.validator_object_txt.null_counts_in_gtfs_obj()
