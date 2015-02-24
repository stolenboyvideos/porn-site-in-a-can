#!/usr/bin/perl

use strict;
use warnings;

use lib '..';
use config;
use query;
use template;

use CGI;
use CGI::Carp 'fatalsToBrowser';

sub error {
    print "Content-type: text/plain\r\n\r\n$_[0]\n";
    exit;
}

# params

my $id = CGI::param('id');

if( ! defined $id or $id !~ m/^\d+$/ ) {
    error("please pass id param");
}

my $user = user() or error("no user record");
my $movie = movie($id) or error("can't find movie of that id");

# movie details

my $mp4 = $movie->mp4 or error("can't find mp4 file for that movie");
my $fn = $config::home . '/video/' . $mp4;
my $s = -s $fn;

# user details

if( $user->bytes_used > $user->bytes_purchased ) {
    error("bytes used up");    
}
$user->bytes_used += $s;
$user->time_last_streamed = scalar time;
$user->write('users');

# stream

print "Content-type: video/mp4\r\n";
print "Content-Length: $s\r\n";
print "\r\n";

exec( '/bin/cat', $fn ) or error("couldn't find cat or the file: $!");

