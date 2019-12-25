from setuptools import setup
import os
# from freecad.workbench_starterkit.version import __version__
# name: this is the name of the distribution.
# Packages using the same name here cannot be installed together

version_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            "freecad", "workbench_gespal3d", "version.py")
with open(version_path) as fp:
    exec(fp.read())

setup(name='freecad.workbench_gespal3d',
      version=str(__version__),
      packages=['freecad',
                'freecad.workbench_gespal3d'],
      maintainer="JW",
      maintainer_email="contact@freecad-france.com",
      url="",
      description="Design gespal3d, wooden crate and packaging.",
      install_requires=[],
      include_package_data=True)
