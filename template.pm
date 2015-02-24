
use strict;
use warnings;

use List::Util 'shuffle';
use CGI;
use Data::Dumper;

use config;
use query;

use sort 'stable'; 

#
# user
#

sub user {

    my $cookie = CGI::cookie('account');
    my $ip = $ENV{'REMOTE_ADDR'};

    my $user;

    ($user) = query("select * from users where cookie = ?", $cookie) if $cookie;
    ($user) = query("select * from users where ip = ?", $ip) if ! $user;

    if( ! $user ) {
        # create a new user if we have to
        my $bytes_purchased = 1 * 1024 * 1024 * 1024;  # 1 free GB
        my $referer = CGI::param('referer') || CGI::param('referrer');    # BTC address to pay referral fees to
        my $user_id = query( "insert into users (ip, time_created, bytes_purchased, bytes_used, referer) values (?, ?, ?, ?, ?)", $ip, scalar time, $bytes_purchased, 0, $referer ); 
        ($user) = query("select * from users where id = ?", $user_id);
    }

    return $user; 

}

#
# movies
#

sub movie {
    my $id = shift or die;
    my ($movie) = query( "select * from movies where disabled is null and id = ?", $id );
    return $movie;
}

sub movies {
    query( "select * from movies where disabled is null order by id desc" );
}

sub some_movies {
    my $movies = shift;
    my $user = shift;
    my $n = shift() || 9;
    my $search = shift;
    my $page = shift;

    my $user_id = $user->id;
    my @movies = @$movies;

    my $predictions = [];
    query( "select rating, movie_id from predictions where user_id = ?", $user->id, sub { my $prediction = shift; $predictions->[ $prediction->movie_id ] = $prediction->rating; } );

    my $compute_rating = sub {
        my $movie = shift;
        if( $predictions && exists $predictions->[ $movie->id ] ) {
            return $predictions->[ $movie->id ];
        } else {
            return $movie->stars || 3;
        }
    };

    if( $search and $search eq 'newest') {

        @movies = reverse @movies;

    } elsif( $search and $search eq 'toprated') {

        # @movies = sort { $b->{stars} <=> $a->{stars} } @movies; # this would be okay except it looks like they aren't sorted because the numbers of stars are all over the place
        @movies = sort { $compute_rating->($b) <=> $compute_rating->($a) } @movies;

    } elsif( $search and $search eq 'popular') {

        @movies = sort { $b->{views} <=> $a->{views} } @movies;

    } elsif( $search ) {

        # sort once for each keyword, starting with the last keyword, which we assume to be less important than the first.
        # if the word is persent in the filename, it gets sorted to the front.
        # this should result in movies with more of the searched for words being closer to the front. 
        # -1 means they're in the proper order; 0 means they compare the same; 1 means they're backwards
        # TODO should remove items from the list that have none of the keywords
        my @keywords = split m/\W+/, $search;
        for my $keyword (reverse @keywords) {
            @movies = sort { 
                my $a_found = index( $a->mp4, $keyword ) >= 0;
                my $b_found = index( $b->mp4, $keyword ) >= 0;
                ( $a_found == $b_found ) ? 0 : ( $a_found && ! $b_found ) ? -1 : 1;
            } @movies;
        }

    } else {

        # default is a random shuffle

        @movies = shuffle( @movies );

    }

    my $num_results = @movies;

    if( $page and $page > 1 ) {
        if( $n * ($page-1) > @movies ) {
            return qq{<div class="rounded">No more results.<br/></div>\n};
        } else {
            splice @movies, 0, $n * ($page-1), ();  # eg, for page 2, get rid of 1 page worth of results off the front
        } 
    }

    my $clip = <<EOF;

      <!--  Video Thumb -->
      <div class="thumb">
    
        <div style="background-image: url(blank.gif);" class="playicon" onmouseover="this.style.backgroundImage='url(play.png)';" onmouseout="this.style.backgroundImage='url(blank.gif)';">
            <a href="/video.cgi/:id:/:partial_filename:"><img src="/blank.gif"></a>
        </div>
    
        <a href="/video.cgi/:id:/:partial_filename:"><img src="/thumbs/:jpg:" width="310" height="235" alt=""></a>

        <div class="thumb-length">
        Time: :time:</div>
    
        <div class="thumb-views">
        Views: :views:</div>
    
        <div class="thumb-stars-:stars:">
        </div>
    
        <div style="clear:both;"></div>
    
      </div>

EOF

    my $content = '';
    
    for my $movie_index ( 1 .. $n ) {
        # my $movie = pop @movies or last;
        my $movie = $movies[$movie_index] or last;

        my $partial_filename = $movie->mp4;
        $partial_filename =~ s{\.\w+$}{};  # remove any file extension
        $partial_filename =~ s{_\d{4,}\.}{};  # remove those wonky uniqe-ifying numbers

        my $rating = $compute_rating->( $movie );

        $content .= template(
            $clip, {
                id => $movie->id,
                views => $movie->views || 0,
                stars => $rating,
                time => $movie->runtime,
                jpg  => $movie->jpg,
                partial_filename => $partial_filename,
            },
        );
    }

    # next/prev page links

    my $prevnext = '';

    if( $page > 1 or @movies > $n ) {

        my $s = CGI::escape($search||'');

        $prevnext .= qq{<br clear="all"><div style="display: block; width: 80%; font-size: 9pt;" class="rounded">\n};

        $prevnext .= qq{<table><tr>};

        $prevnext .= qq{<td width="20%">};
        if( $page > 1 ) {
            $prevnext .= qq{
                <a href="?s=$s&p=@{[ $page-1 ]}">&lt;&nbsp;&lt;&nbsp;&lt;&nbsp;Previous&nbsp;&nbsp;</a>
            };
        } else {
            $prevnext .= qq{&lt;&nbsp;&lt;&nbsp;&lt;&nbsp;Previous&nbsp;&nbsp;};
        }
        $prevnext .= qq{</td>};

        $prevnext .= qq{<td width="60%">};
        my $m = int( $num_results / $n );
        $m++ if $num_results % $n;   # round up if there are results left after the last full page
        my $i = 0;
        while( $i < $m ) {
            $prevnext .= qq{ &dot; } if $i > 0;
            $prevnext .= qq{<a href="?s=$s&p=$i">@{[ $i+1 ]}</a>};
            $i++;
        }
        $prevnext .= qq{</td>};

        $prevnext .= qq{<td width="20%">};
        if( @movies > $n ) {
            $prevnext .= qq{<a href="?s=$s&p=@{[ $page+1 ]}">&nbsp;&nbsp;Next&nbsp;&gt;&nbsp;&gt;&nbsp;&gt;</a>};
        } else {
            $prevnext .= qq{&nbsp;&nbsp;Next&nbsp;&gt;&nbsp;&gt;&nbsp;&gt;};
        }
        $prevnext .= qq{</td>};

        $prevnext .= qq{</tr></table>};

        $prevnext .= qq{</div>\n};

    }

    return wantarray ? ( $content, $prevnext ) : $content;
}

#
# template
#

sub template {

    my $page = shift;
    my $args = shift;

    if( ! $page ) {
        open my $fh, '<', 'template.html' or die $!;
        $page = join '', readline $fh;
    }

    # $page =~ s{<!-- $section CONTENT START -->.*<!-- $section CONTENT STOP -->}{};

    $page =~ s{:(\w+):}{ $args->{$1} }ge;

    return $page;

}

1;
