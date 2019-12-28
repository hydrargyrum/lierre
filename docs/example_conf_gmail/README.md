# Example GMail configuration

## pass: password storage

To avoid asking passwords everytime, a password manager can be used, like [pass](https://www.passwordstore.org/).
Password are encrypted using gpg.

If you never used gpg and pass before:

    gpg --quick-generate-key password-store
    pass init password-store
    pass insert gmail

Warning: GMail requires a manual action from you to enable IMAP access and another to set a dedicated IMAP password. Insert the specific IMAP password in `pass`.

## mbsync: syncing mail

[mbsync](http://isync.sourceforge.net/mbsync.html) is a tool to synchronize an IMAP server with a local Maildir folder.
It will download mails from the IMAP server, but is also able to push local draft saving, propagate deletions, etc.

Copy mbsyncrc to ~/.mbsyncrc and configure the file.

## msmtp: sending mail

[msmtp](https://marlam.de/msmtp/) is a tool to send emails with SMTP.

Copy msmtprc to ~/.msmtprc and configure the file.

## lierre: glueing together

Copy lierre_config to ~/.config/lierre/config and configure the file.
