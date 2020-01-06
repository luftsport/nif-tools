.. Nif Tools documentation master file, created by
   sphinx-quickstart on Mon Jan  6 19:40:13 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Nif Tools's documentation!
=====================================

.. danger::
   Incomplete module


***************
NIF Tools
***************
A set of tools based upon requests to programatically interact with the web instances at minidrett, ka and sa.nif.no.


Login::

   from nif-tools import passbuy

   pb = Passbuy(username='username', password='password', realm='ka', verify=True)
   status, person_id, fed_cookie_jar = pb.login()
   if status is True:
       print('Person Id:', person_id)

Get list of clubs from KA::

   from nif_tools import KA
   ka = KA(username='username', password='password')
   clubs = ka.get_clubs()


.. toctree::
   :maxdepth: 1
   :caption: NIF Tools

   mi
   ka
   sa

.. toctree::
   :maxdepth: 1
   :caption: Passbuy

   passbuy

.. toctree::
   :maxdepth: 1
   :caption: Common functions

   common



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


Recent Changes
--------------

.. git_changelog::