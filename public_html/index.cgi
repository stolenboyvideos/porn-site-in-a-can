#!/usr/bin/perl

use strict;
use warnings;

use CGI;
use CGI::Carp 'fatalsToBrowser';

use lib "..";
use config;
use query;
use template;

print "Content-type: text/html\r\n\r\n";

my $user = user();

my $search = CGI::param('s');
my $page = CGI::param('p');

my $movies = movies();

(my $content, my $prevnext) = some_movies( $movies, $user, 138, $search, $page, );

print template( undef, {
    content => $content,
    prevnext => $prevnext,
    num_videos => $movies->num_rows,
    logged_in => ($user->cookie ? 1 : 0),
} );


