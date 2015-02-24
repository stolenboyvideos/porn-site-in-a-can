#!/usr/bin/perl

use strict;
use warnings;

use CGI;
use CGI::Carp 'fatalsToBrowser';

use lib '..';
use template;

print "Content-type: text/html\r\n\r\n";

my $user = user();

my $movies = movies();

my $content = << 'EOF';

N'yet.

EOF

print template( undef, {
    content => $content,
    num_videos => $movies->num_rows,
    logged_in => ($user->cookie ? 1 : 0),
} );


