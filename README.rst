
=================
ShotMaker [0.2.0]
=================

This is the ShotMaker application.


Minimum Requirements
====================

- Python 2.7


Optional Requirements
=====================

.. _pytest: http://pytest.org
.. _Sphinx: http://sphinx-doc.org

- `pytest`_ (for running the test suite)
- `Sphinx`_ (for generating documentation)


Basic Setup
===========

You can create and run the test suite by:

creating a test folder on root and write a test code in it using pytest module.

And to run it use:

.. code-block:: console
   
    $ pytest test/


Build documentation:

.. code-block:: console

    $ cd doc && make html
    
    
Deploy the application in a self-contained `Virtualenv`_ environment:

.. _Virtualenv: https://virtualenv.readthedocs.org

.. code-block:: console

    $ python deploy.py /path/to/apps
    $ cd /path/to/apps/ShotMaker && bin/cli --help
