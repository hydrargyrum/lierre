Lierre - refreshing
===================

.. TODO link to "plugins" page
.. TODO describe that plugins are not the real tools, they merely run the tools, so the tools must be configured

Lierre run fetcher plugins (running tools like mbsync). Those should contact email servers and download new emails into the local Maildir.

Lierre then runs `notmuch-new` to index these new emails.

Lierre then runs filter plugins to do some automatic processing on emails, like attributing some tags.
