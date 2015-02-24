#!/usr/bin/perl

use strict;
use warnings;

use CGI;
use CGI::Carp 'fatalsToBrowser';

use JSON::PP;

use lib '..';
use config;
use template;
use query;

#
#
#

print "Content-type: application/json\r\n\r\n";

sub error {
    my $message = shift;
    print encode_json { error => $message, };
    exit;
}

#
# get the user_id of the user
#

my $user = user() or error "Can't find a user";
my $user_id = $user->id or error "no user_id";

#
# get the specified movie and number of stars
#

my $movie_id = CGI::param('movie_id');
defined $movie_id or error "No id of a movie passed";
my $movies = movie($movie_id) or error("can't find movie of that id");

my $stars = CGI::param('stars') or error "No value passed for stars";
grep $stars eq $_, 1, 2, 3, 4, 5 or error "Can only rate things 1, 2, 3, 4, or 5 stars";

#
# record this ranking keyed by this user for this movie so they can't vote twice
#

my ($existing_movie_rating_by_this_user) = query( "select * from ratings where user_id = ? and movie_id = ? ", $user_id, $movie_id );

if( $existing_movie_rating_by_this_user ) {
    # update an existing rating
    query( "update ratings set rating = ? where user_id = ? and movie_id = ?", $stars, $user_id, $movie_id );
} else {
    # add a new rating
    query( "insert into ratings (rating, user_id, movie_id) values (?, ?, ?)", $stars, $user_id, $movie_id );
}

# update the ranking of the movie
# average all of the rankings; slow

my ($movie_rating) = query( "select sum(rating) / count(*) as movie_rating from ratings where movie_id = ?", $movie_id, sub { $_->{movie_rating} + 0.5 }, ); # round to nearest number of stars
$movie_rating = int $movie_rating;

query( "update movies set stars = ? where id = ?", $movie_rating, $movie_id );

print encode_json { ok => 1, };

#
# experimental:  re-run predictions after every vote
#

close STDOUT;
open STDOUT, '>>', $config::home . '/predict.log';

exec '/usr/bin/perl', 'predict.cgi';
