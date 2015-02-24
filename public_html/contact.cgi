#!/usr/bin/perl

use strict;
use warnings;

use CGI;
use CGI::Carp 'fatalsToBrowser';

use lib '..';
use config;
use template;
use query;

print "Content-type: text/html\r\n\r\n";

my $user = user();

my $comment_text = CGI::param('comment');

my $content;

if( $comment_text ) {
    query( "insert into comments (user_id, timestamp, comment) values (?, ?, ?)", $user->id, scalar time, $comment_text, );

    $content = '<br/><br/>Comment recorded.  Thank you for taking time to write.<br/><br/>';

} else {

    $content = <<'EOF';

<br/><br/>

Problem reports, copyright violation notifications (with required details), and feedback are welcome, but we are not able to respond to all comments individually.<br/></br>

<form method="post">
<textarea rows="5" cols="80" name="comment">
</textarea>
<br/><br/>
<input type="submit" value="Send Message">
</form>

EOF

}

my $movies = movies();

print template( undef, {
    content => $content,
    num_videos => $movies->num_rows,
    logged_in => ($user->cookie ? 1 : 0),
} );


