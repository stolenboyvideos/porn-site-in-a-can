#!/usr/bin/perl

# generate a set of predicted movie ratings for users who have rated some movies

use strict;
use warnings;

use lib '..';
use config;
use template;
use query;

use CGI;
use CGI::Carp 'fatalsToBrowser';

use JSON::PP;
use Data::Dumper;

my ($num_users) = query( "select count(*) as num from users", sub { $_[0]->num }, );
my ($num_movies) = query( "select count(*) as num from movies where disabled is null", sub { $_[0]->num }, );

#

print "Content-type: text/plain\r\n\r\n";

*STDERR = *STDOUT; # debugging

# use lib $config::home . '/lib64/perl5/site_perl/5.8.8/x86_64-linux-thread-multi/'; # have to do something like this for shared hosting

use Math::Preference::SVD;

print "ok\n";

# build a list of users who we can build predictions for

my $ratings = query( "select * from ratings" );

my %users_who_have_rated_something;
for my $rating ( @$ratings ) {
    $users_who_have_rated_something{ $rating->{user_id} }++;  # TODO could use this to restrict who gets ratings (eg three or more movies)
}

# convert our ratings to what M::P::SVD wants

my @ratings = map [ $_->{user_id}, $_->{movie_id}, $_->{rating} ],  @$ratings;

my $svd = Math::Preference::SVD->new;

$svd->set_ratings( \@ratings, );

# regenerate the predictions from scratch

query( "delete from predictions" );

my $num_predictions = 0;

for my $movie_id ( 0 .. $num_movies-1 ) {
    for my $user_id ( sort { $a <=> $b } keys %users_who_have_rated_something ) {
        # "predict_rating() takes movie_id then cust_id -- yes, this seems backward to me too"
        my $predicted_rating = int( 0.5 + $svd->predict_rating($movie_id, $user_id) );  # the 0.5 is supposed to round to the nearest star; without it, int() would just truncate
        $num_predictions++;
        query( "insert into predictions (rating, user_id, movie_id) values (?, ?, ?)", $predicted_rating, $user_id, $movie_id );
    }
}

print "$num_predictions predictions made on $num_movies movies for @{[ scalar keys %users_who_have_rated_something ]} out of $num_users users\n";



