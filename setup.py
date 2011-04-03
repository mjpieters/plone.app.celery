from setuptools import setup, find_packages
import os

version = '1.0'

setup(name='plone.app.celery',
      version=version,
      description="Celery integration for Plone",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        ],
      keywords='celery, plone, distributed, task queue',
      author='Jarn AS',
      author_email='info@jarn.com',
      url='http://pypi.python.org/pypi/plone.app.celery',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['plone', 'plone.app'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'celery',
          'zope.tales',
      ],
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
