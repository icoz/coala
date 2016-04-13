import calendar
import os
import pickle
import time

from coalib.misc.Constants import caching_db, changed_files_db
from coalib.output.Tagging import get_tags_dir as get_pickle_dir


def get_cache_data_path(log_printer, filename):
    """
    Get the full path of ``filename`` present in the user's cache directory.

    :param log_printer: A LogPrinter object to use for logging.
    :param filename:    The file whose path needs to be expanded.
    :return:            Full path of the file, assuming it's present in the
                        user's config directory.
    """
    return os.path.join(get_pickle_dir(log_printer), filename)


def delete_cache_files(log_printer, files=[caching_db, changed_files_db]):
    """
    Delete the cache files after displaying a warning saying the cache
    is corrupted and will be removed.

    :param log_printer: A LogPrinter object to use for logging.
    :param files:       The list of files to be deleted.
    :return:            True if all the given files were successfully deleted.
                        False otherwise.
    """
    log_printer.warn("The caching database is corrupted and will "
                     "be removed. Each project will be re-cached "
                     "automatically the next time coala is run.")
    error_files = []
    for file_name in files:
        file_path = get_cache_data_path(log_printer, file_name)
        cache_dir = os.path.dirname(file_path)
        try:
            os.remove(file_path)
        except OSError:
            error_files.append(file_name)

    if len(error_files) > 0:
        error_files = ", ".join(error_files)
        log_printer.warn("There was a problem deleting the following "
                         "files: " + error_files + ". Please delete "
                         "them manually from " + cache_dir)
        return False

    return True


def pickle_load(log_printer, filename, fallback=None):
    """
    Get the data stored in ``filename`` present in the coala user
    config directory. Example usage:

    >>> from pyprint.NullPrinter import NullPrinter
    >>> from coalib.output.printers.LogPrinter import LogPrinter
    >>> log_printer = LogPrinter(NullPrinter())
    >>> test_data = {"answer": 42}
    >>> pickle_dump(log_printer, "test_file", test_data)
    >>> pickle_load(log_printer, "test_file")
    {'answer': 42}
    >>> pickle_load(log_printer, "nonexistant_file")
    >>> pickle_load(log_printer, "nonexistant_file", fallback=42)
    42


    :param log_printer: A LogPrinter object to use for logging.
    :param filename:    The name of the file present in the coala user config
                        directory.
    :param fallback:    Return value to fallback to in case the file doesn't
                        exist.
    :return:            Data that is present in the file, if the file exists.
                        Otherwise the ``default`` value is returned.
    """
    filename = get_cache_data_path(log_printer, filename)
    if not os.path.isfile(filename):
        return fallback
    with open(filename, "rb") as f:
        try:
            return pickle.load(f)
        except (pickle.UnpicklingError, EOFError) as e:
            delete_cache_files(log_printer, files=[filename])
            return fallback


def pickle_dump(log_printer, filename, data):
    """
    Write ``data`` into the file ``filename`` present in the coala user
    config directory.

    :param log_printer: A LogPrinter object to use for logging.
    :param filename:    The name of the file present in the coala user config
                        directory.
    :param data:        Data to be serialized and written to the file using
                        pickle.
    """
    filename = get_cache_data_path(log_printer, filename)
    with open(filename, "wb") as f:
        return pickle.dump(data, f)


def add_to_changed_files(log_printer, project_dir, changed_files):
    """
    Save the set of files in ``changed_files`` to disk for future use
    in ``update_last_coala_run_time``.

    :param log_printer:   A LogPrinter object to use for logging.
    :param project_dir:   The root directory of the project on which
                          coala is to be run.
    :param changed_files: A set of files that had changed since the last
                          time coala was run.
    """
    data = pickle_load(log_printer, changed_files_db, {})

    if project_dir in data:
        data[project_dir].update(changed_files)
    else:
        data[project_dir] = changed_files

    pickle_dump(log_printer, changed_files_db, data)


def get_last_coala_run_time(log_printer, project_dir):
    """
    Get the last time coala was run on the project in epoch format
    (number of seconds since Jan 1, 1970).

    :param log_printer: A LogPrinter object to use for logging.
    :param project_dir: The root directory of the project on which
                        coala is to be run.
    :return:            Returns a dict of files with file path as key
                        and the last time that coala was run on that file
                        as value. Returns None if this is the first time coala
                        is run on that project.
    """
    data = pickle_load(log_printer, caching_db, {})
    return data.get(project_dir, None)


def add_new_files_since_last_run(log_printer, project_dir, last_coala_run,
                                 new_files):
    """
    Start tracking new files given in ``new_files`` by adding them to the
    database.

    :param log_printer:    A LogPrinter object to use for logging.
    :param project_dir:    The root directory of the project on which
                           coala is to be run.
    :param last_run_coala: Previously available data to which the new files
                           need to be appended.
    :param new_files:      The list of new files that need to be tracked.
                           These files are initialized with their last
                           modified tag as -1.
    """
    if last_coala_run is None:
        last_coala_run = {}
    for new_file in new_files:
        last_coala_run[new_file] = -1
    data = pickle_load(log_printer, caching_db, {})
    data[project_dir] = last_coala_run
    pickle_dump(log_printer, caching_db, data)


def update_last_coala_run_time(log_printer, project_dir):
    """
    Update the last time coala was run on the project for each file
    to the current time.

    :param log_printer: A LogPrinter object to use for logging.
    :param project_dir: The root directory of the project on which
                        coala is to be run.
    """
    current_time = calendar.timegm(time.gmtime())
    data = pickle_load(log_printer, caching_db, {})
    changed_files = pickle_load(log_printer, changed_files_db, {})

    # update_last_coala_run_time is always ran after
    # add_new_files_since_last_run, or the project has already been
    # initialized in the caching database.
    if project_dir not in data:
        return

    for file_name in data[project_dir]:
        if (project_dir not in changed_files or
                file_name not in changed_files[project_dir]):
            data[project_dir][file_name] = current_time
    changed_files[project_dir] = set()
    pickle_dump(log_printer, caching_db, data)
    pickle_dump(log_printer, changed_files_db, changed_files)
