Tempoggl
========

Tool for semi-automatic syncing of Jira Tempo entries into Toggl.

::

  usage: tempoggl [-h] [--username USERNAME] [-y] [--from YYYY-MM-DD] [-v]
                  [-j JIRA_URL] [-t TOGGL_TOKEN] [-m [KEY=ID [KEY=ID ...]]]

  Sync time tracking entries from Jira Tempo app into Toggl. Prompt before
  pushing any changes.

  optional arguments:
    -h, --help            show this help message and exit
    --username USERNAME   jira username
    -y, --yes             answer yes when prompted
    --from YYYY-MM-DD     sync all entries from this date
    -v, --verbose         print more information
    -j JIRA_URL, --jira-url JIRA_URL
                          root url for jira e.g. https://jira.example.com
    -t TOGGL_TOKEN, --toggl-api-token TOGGL_TOKEN
                          get from here https://toggl.com/app/profile
    -m [KEY=ID [KEY=ID ...]], --toggl-mapping [KEY=ID [KEY=ID ...]]
                          map jira project key to toggl project id. For example
                          "--toggl-mapping PROJ=456 ABCD=5432 MISC=9876"


Installation
------------

``$ pip3 install https://github.com/je-l/tempoggl``

Usage
-----

* ``$ tempoggl today``
* ``$ tempoggl week``
* ``$ tempoggl YYYY-MM-DD``


Configuration
-------------

By default the config file is created at ``~/.config/tempoggl/tempoggl.cfg``

::

  [general]
  username: user.name@jira.com
  jira_url: https://jira.example.com

  [toggl_mapping]
  jira project key to toggl project id
  PROJ: 123456
