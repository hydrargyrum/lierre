Lierre - plugins
================

Lierre tries to provide a minimal core, delegating to other tools the heavylifting work of email manipulation.
However, multiple existing tools are supported as alternatives.

.. TODO link to "plugin development" page

Fetcher plugins
---------------

Fetcher plugins synchronize emails from a mail server (most often an IMAP server) to a local mailbox directory.
The local mailbox directory should be in Maildir++ format, as this is the format `notmuch` supports.

.. TODO dedicated pages for each plugin
.. TODO configuration of each plugin in lierre
.. TODO configuration of the underlying tool

* `mbsync`
* `command`

Filter plugins
--------------

.. TODO link to "refresh process" page

Filter step are run within a "refresh", after the fetching step.
Filter plugins can do many things, for example set tags automatically basing on mail content (sender, attachments, spam/ham).

* `command`
* `trashing`

Sender plugins
--------------

Sender plugins are sending emails (most often to an SMTP server). They do not care about saving the email in a "Sent" folder or anything, just sending.

* `msmtp`
* `sendmail`

Address book plugins
--------------------

.. TODO

Address book plugins are typically used for recipient autocompletion/suggestion when composing an email.

* `khard`

Other plugins
-------------

These are plugins that are not in the previous categories. They can react to many events.
Some are UI plugins, some other are email plugins.

UI plugins:

* `tag_colors`
* `notifications`

Email plugins

* `imapidle`
* `periodic_refresh`
