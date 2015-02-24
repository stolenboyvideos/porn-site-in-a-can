#!/usr/bin/perl

use strict;
use warnings;

use lib '..';
use template;
use query;

use CGI;
use CGI::Carp 'fatalsToBrowser';

#
# read required video id
#

(my $id) = $ENV{PATH_INFO} =~ m{^/(\d+)/};

if( ! defined $id or $id !~ m/^\d+$/ ) {
    print "Location:  http://$ENV{HTTP_HOST}\r\n\r\n";
    exit;
}

#
# figure out if the user is out of data
#

my $user = user();
my $user_id = $user->id;

if( $user->bytes_used > $user->bytes_purchased ) {
    print "Location:  http://$ENV{HTTP_HOST}/register.cgi\r\n\r\n";
    exit;
}

#
# get movie information to fetch the rating and bump the views count
#

my $movies = movies();
my($movie) = grep $_->id == $id, @$movies or die "can't find movie of that id";
$movie->views ++;
$movie->write('movies');

#
# show video
#

print "Content-type: text/html\r\n\r\n";

my $clip = <<'EOF';

   <!-- thumbnail hopefully visible to search engines since the poster thing is kinda wonky and not standard -->
   <div style="display: none;"><img src="/thumbs/:jpg:"></div>

   <!-- player -->

   <div style="width: 90%; float: left;">
   <div id="player" class="flowplayer no-background" data-swf="flowplayer.swf" data-ratio="0.4167">
      <video autoplay poster="/thumbs/:jpg:">
         <source type="video/:type:" src="/stream.cgi?id=:id:">
      </video>
   </div>
   </div>

    <!-- control to rate this -->

    <div class="rounded" style="float:right;">
        Rate this video<br/>
        <div class="thumb-stars-:stars: rate-movie">
        </div>
    </div>

    <!-- pop-up with more videos to watch -->

    <div id="morevideos">
        <div style="float: right"><img src="/close_sm.png" onclick="hide_other_videos();"></div>
        :more_movies_content:
    </div>

<script type="text/javascript">

<!-- hide/show the "more videos" pop up -->

function show_other_videos() {
    if( $('#morevideos').css('display') == "none" ) {  // otherwise, this getting triggered twice in a row causes it to be shown and then hidden again immediately
        $('#morevideos').animate({
            height:  'toggle',
        }, 'slow');
    }
}

function hide_other_videos() {
     $('#morevideos').hide();
}

flowplayer(function (api, root) {
  api.bind("pause", show_other_videos)
     .bind("finish", show_other_videos);
  api.bind("resume", hide_other_videos);
  api.bind("error", function(event, player, error) { location.reload(); }); // XXX might be a less crude way to retry
});

$(document).ready(function() {

    $('.rate-movie').click( function(e) {
        var offset = $(this).offset();
        var pixels = e.clientX - offset.left;
        // 17, 34, 51, 68, 84.... basically, / 17
        var stars = Math.round( pixels / 17 );
        var rate_control = $(this);

        $.ajax({
            url: "/rate.cgi?movie_id=:id:&stars=" + stars,
        }).done(function( res ) {
            if( res.error ) {
                alert( res.error );
            } else {
                rate_control.removeClass('thumb-stars-1 thumb-stars-2 thumb-stars-3 thumb-stars-4 thumb-stars-5');
                rate_control.addClass('thumb-stars-' + stars); 
            }
        });

     });
});

</script>


EOF

#
# get content to show for the 'moremovies' display and insert it
#

my $more_movies = some_movies( $movies, $user, 9 );


#
# figure out how many stars this user rated this movie, and show them their own rating if they gave it one; otherwise, show the actual rating or default
#

(my $existing_movie_rating_by_this_user) = query("select rating from ratings where user_id = ? and movie_id = ?", $user_id, $id, sub { $_[0]->rating } );
my $stars = $existing_movie_rating_by_this_user ? $existing_movie_rating_by_this_user : $movie->stars || 3;

#
# template the 'view movie' content
#

my $content = template(
    $clip, {
        id   => $id,                           # id of the movie to stream
        type => 'mp4',                         # type of the movie to stream; flowplayer also supports webm
        more_movies_content => $more_movies,   # more movies to view if they pause or finish this one
        stars => $stars,
        jpg  => $movie->jpg,
    },
);

#
# insert that into the main page template
#

print template( undef, {
    content => $content,
    num_videos => $movies->num_rows,
    logged_in => ($user->cookie ? 1 : 0),
} );


