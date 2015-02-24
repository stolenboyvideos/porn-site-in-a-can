
# Porn Site in a Can

Ready to deploy and configure adult video site.  Or make a non-porn tube site out of it.

No porn included -- this is only code (and certainly not good enough code to be considered code porn).

## Features

* Automatic indexing, conversion, and thumbnailing of video files
* Leech protection
* Netflix style "users with similar taste also liked" recommendations
* 100% ready to receive Bitcoin payments out of the box
* Referal system with automatic, "instant" payouts
* One-click account creation (really!)
* Runs on cPanel powered shared hosts (except for referal payouts)

## Why?

I like Bitcoin.  The web has despretely needed a micropayment system that
allows content creators and users an alternative to ads or credit card
subscriptions, which pay poorly and are a poor value to both you and users.
I think Bitcoin is going to revolutionize the Web.
Starting with adult content sites seems logical.

I want the consulting business.  I will extend and customize this code for
money (Bitcoin, of course).  Why better to hire than the person who wrote it?
Or I'll work on your own project.

## Todo

* User upload of video feature
* Management interface
* Better documentation/easier install

## Technical Details

Currently requiers a VPS host, or a Mac or Linux client machine, to import videos.
Implemented mostly in Perl for security and out-of-the-box support on shared
hosts and VPS installs.
MySQL database (commonly available on shared hosts).
FlowPlayer (can easily be changed out).
jQuery/jQuery-UI powered interface.
Uses http://blockchain.info/api/receive to accept payments.
Uses XML-RPC to interface with the Bitcoin Core standard Bitcoin server
daemon for referal payouts.

## Installation

The files in the root should not be shared on the Web.  The files inside
the `public_html` directory should be.

The `.cgi` scripts assume that the private files are one directory up
(`use lib '..';`).  Change that line in each `.cgi` file if they are
moved to somewhere else.

If the `.cgi` scripts and `thumbs` directory are somewhere else, create
a `public_html` symlink to them from the private directory (which contains `video` and the `.pm` files.
For example:

    ln -s /path/to/pm/files/and/video/directory /path/to/web_root/public_html

`upload.pl` currently needs this to find where to put the static thumbnails.

Copy `config.pm.example` to `config.pm` and edit it for your domain 
name, directory locations, Bitcoin address for payments, MySQL
connection information, and so on.

Creating these files while running as the web user, or chown them to the web user:

```
touch debug.log
touch predict.log
mkdir video
mkdir public_html/video
```

Configure MySQL, including creating a database (`create database <whatever>`)
and creating a user with a password to access it:
http://dev.mysql.com/doc/refman/4.1/en/user-account-management.html,
or use your host's control panel to configure MySQL.

Create these tables in MySQL:

```
create table users (
    id int auto_increment key,
    ip varchar(15), cookie varchar(200), bytes_purchased int, bytes_used int, time_created int, time_last_streamed int, debug varchar(1024), payment_status varchar(1024), referer varchar(36),
    index (ip), index(cookie) -- not 'unique' becaue multiple will be null
);

create table movies (
    id int auto_increment key,
    mp4 varchar(200), jpg varchar(200), views int, stars int, runtime varchar(10), md5 varchar(32), disabled varchar(100)
);

create table ratings (
    user_id int not null,  movie_id int not null, rating int,
    index (user_id), index(movie_id), index(rating)
);

create table predictions (
    user_id int not null, movie_id int not null, rating int not null,
    index (user_id), index(movie_id), index(rating)
);

create table purchases (user_id int, bytes_purchased int, btc float);
```

Perl modules:

```
LWP
JSON
DBD
MD5
DBI::mysql
List::MoreUtils
Math::Preference::SVD
```

Debian packages:

```
build-essential
libmysqlclient-dev
libmysqld-dev
libssl-dev
mysql-client
mysql-server
perl-doc
netpbm
ffmpeg
libjpeg-progs
pvrg-jpeg
```

Also requires `qtfaststart` for importing videos:  https://github.com/danielgtaylor/qtfaststart.

Use `upload.pl` to import movies.
If you're using a shared host, try using `sshfs` to mount the remote machine as a directory on your local machine, and run `uplaod.pl` on your local machine (Mac or Linux).

## License

GPL Free Software/Open Source:  http://www.gnu.org/licenses/gpl-2.0.html

BECAUSE THE PROGRAM IS LICENSED FREE OF CHARGE, THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. 

Additionally, no warranty is made as to the security of any Bitcoin wallets used or accessible by this software.

Contains jQuery, FlowPlayer, and other open source software.
Please see their individual licenses referenced from the individual files.

## Contact

Message me on Reddit:  http://www.reddit.com/user/stolenboyvideos

## See Also

* Announcement/Motivation/Discussion:  http://www.reddit.com/r/Bitcoin/comments/2wr30a/nsfw_evil_gay_opposite_twin_of_the_been_accepting/
* Example:  http://stolenboyvideos.com

