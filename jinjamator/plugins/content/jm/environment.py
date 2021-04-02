import logging
import os

log = logging.getLogger()


def site_path():
    return _jinjamator._configuration.get("jinjamator_site_path", None)


def jinjamator_base_directory():
    return _jinjamator._configuration.get("jinjamator_base_directory", None)


def jinjamator_global_tasks_base_dirs():
    return _jinjamator._configuration.get("global_tasks_base_dirs", None)


def python_requirements():
    path = os.path.join(jinjamator_base_directory(), "requirements.txt")
    with open(path, "r") as fh:
        return fh.read().split("\n")


def get(var, default=None):
    """
    jinja2 helper function to access the os environment
    """

    return os.environ.get(var, default)


def pop(var, default=None):
    """
    jinja2 helper function to access the os environment
    """
    try:
        data = os.environ.pop(var)
    except KeyError:
        data = default
    return data
