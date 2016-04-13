import os
import unittest

from pyprint.NullPrinter import NullPrinter

from coalib.misc.Caching import (
    get_cache_data_path, pickle_load, pickle_dump, add_to_changed_files,
    add_new_files_since_last_run, get_last_coala_run_time,
    update_last_coala_run_time, delete_cache_files)
from coalib.output.printers.LogPrinter import LogPrinter


class CachingTest(unittest.TestCase):

    def setUp(self):
        self.log_printer = LogPrinter(NullPrinter())

    def test_pickling(self):
        test_data = {"answer": 42}

        pickle_dump(self.log_printer, "test_file", test_data)
        self.assertEqual(pickle_load(self.log_printer, "test_file"), test_data)
        os.remove(get_cache_data_path(self.log_printer, "test_file"))

        self.assertEqual(pickle_load(
            self.log_printer, "nonexistant_file"), None)
        self.assertEqual(pickle_load(
            self.log_printer, "nonexistant_file", fallback=42), 42)

    def test_add_new_files_since_last_run(self):
        add_new_files_since_last_run(
            self.log_printer,
            "coala_test",
            {},
            ["test.c", "file.py"])
        data = get_last_coala_run_time(self.log_printer, "coala_test")
        self.assertEqual(data, {"test.c": -1, "file.py": -1})

    def test_corrupt_cache_files(self):
        file_path = get_cache_data_path(self.log_printer, "corrupt_file")
        with open(file_path, "wb") as f:
            data = [1] * 100
            f.write(bytes(data))

        self.assertTrue(os.path.isfile(file_path))
        self.assertEqual(pickle_load(
            self.log_printer, "corrupt_file", fallback=42), 42)
        self.assertFalse(os.path.isfile(file_path))

    def test_update_last_coala_run_time(self):
        add_new_files_since_last_run(
            self.log_printer,
            "coala_test",
            {},
            ["test.c"])

        data = get_last_coala_run_time(self.log_printer, "coala_test")
        self.assertEqual(data["test.c"], -1)

        update_last_coala_run_time(self.log_printer, "coala_test")
        data = get_last_coala_run_time(self.log_printer, "coala_test")
        self.assertNotEqual(data["test.c"], -1)

        add_new_files_since_last_run(
            self.log_printer,
            "coala_test2",
            {},
            ["test.c"])
        data = get_last_coala_run_time(self.log_printer, "coala_test2")
        self.assertEqual(data["test.c"], -1)

        update_last_coala_run_time(self.log_printer, "coala_test2")
        data = get_last_coala_run_time(self.log_printer, "coala_test2")
        self.assertNotEqual(data["test.c"], -1)

    def test_add_to_changed_files(self):
        add_new_files_since_last_run(
            self.log_printer, "coala_test",
            {},
            ["test.c"])

        data = get_last_coala_run_time(self.log_printer, "coala_test")
        self.assertEqual(data["test.c"], -1)

        update_last_coala_run_time(self.log_printer, "coala_test")
        data = get_last_coala_run_time(self.log_printer, "coala_test")
        old_time = data["test.c"]
        add_to_changed_files(self.log_printer, "coala_test", {"test.c"})
        update_last_coala_run_time(self.log_printer, "coala_test")
        self.assertEqual(old_time, data["test.c"])

        add_new_files_since_last_run(
            self.log_printer,
            "coala_test",
            {},
            ["a.c", "b.c"])
        old_data = get_last_coala_run_time(self.log_printer, "coala_test")
        add_to_changed_files(self.log_printer, "coala_test", {"a.c"})
        update_last_coala_run_time(self.log_printer, "coala_test")
        new_data = get_last_coala_run_time(self.log_printer, "coala_test")
        # Since b.c had not changed, the time would have been updated.
        self.assertNotEqual(old_data["b.c"], new_data["b.c"])
        # Since a.c had changed, the time would still be the initial
        # value of -1.
        self.assertEqual(old_data["a.c"], new_data["a.c"])

    def test_delete_cache_files(self):
        pickle_dump(self.log_printer, "coala_test", {"answer": 42})
        self.assertTrue(delete_cache_files(
            self.log_printer, files=["coala_test"]))
        self.assertFalse(os.path.isfile(get_cache_data_path(
            self.log_printer, "coala_test")))
        self.assertFalse(delete_cache_files(
            self.log_printer, files=["non_existant_file"]))
